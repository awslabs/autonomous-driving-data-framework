#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License").
#    You may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


import json
import logging
import os
import random
import string
import textwrap
from datetime import timedelta
from typing import TypeVar

import boto3
from airflow import DAG, settings
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.exceptions import AirflowException
from airflow.models import Connection
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.batch import AwsBatchOperator
from sagemaker.processing import Processor, ProcessingInput, ProcessingOutput
from sagemaker.pytorch.processing import PyTorchProcessor
from sagemaker.session import Session

from airflow.utils.dates import days_ago
from boto3.dynamodb.conditions import Key
from boto3.session import Session
from mypy_boto3_batch.client import BatchClient

from image_dags import batch_creation_and_tracking
from image_dags.dag_config import ADDF_MODULE_METADATA, DEPLOYMENT_NAME, MODULE_NAME, REGION

# SET MODULE VARIABLES FOR IMAGE EXTRACTION
PROVIDER = "FARGATE"  # One of ON_DEMAND, SPOT, FARGATE
FILE_SUFFIX = ".bag"
VCPU = "4"
MEMORY = "16384"
CONTAINER_TIMEOUT = 300  # Seconds - must be at least 60 seconds
IMAGE_TOPICS = ["/flir_adk/rgb_front_left/image_raw", "/flir_adk/rgb_front_right/image_raw"]
DESIRED_ENCODING = "bgr8"

# SET MODULE VARIABLES FOR OBJECT DETECTION
MODEL = "yolov5s"
YOLO_INSTANCE_TYPE = "ml.m5.xlarge"


# GET MODULE VARIABLES FROM APP.PY AND DEPLOYSPEC
addf_module_metadata = json.loads(ADDF_MODULE_METADATA)

DAG_ROLE = addf_module_metadata["DagRoleArn"]
DYNAMODB_TABLE = addf_module_metadata["DynamoDbTableName"]
ECR_REPO_NAME = addf_module_metadata["EcrRepoName"]
FARGATE_JOB_QUEUE_ARN = addf_module_metadata["FargateJobQueueArn"]
ON_DEMAND_JOB_QUEUE_ARN = addf_module_metadata["OnDemandJobQueueArn"]
SPOT_JOB_QUEUE_ARN = addf_module_metadata["SpotJobQueueArn"]
TARGET_BUCKET = addf_module_metadata["TargetBucketName"]

account = boto3.client("sts").get_caller_identity().get("Account")

ValueType = TypeVar("ValueType")

DAG_ID = os.path.basename(__file__).replace(".py", "")
TASK_DEF_XCOM_KEY = "job_definition_arn"

DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["airflow@example.com"],
}

logger = logging.getLogger("airflow")
logger.setLevel("DEBUG")


def try_create_aws_conn():
    conn_id = "aws_default"
    try:
        AwsHook.get_connection(conn_id)
    except AirflowException:
        extra = json.dumps({"role_arn": DAG_ROLE}, indent=2)
        conn = Connection(conn_id=conn_id, conn_type="aws", host="", schema="", login="", extra=extra)
        try:
            session = settings.Session()
            session.add(conn)
            session.commit()
        finally:
            session.close()


def create_batch_of_drives(ti, **kwargs):
    """
    if Batch Id already exists, then skip
    List Drive Folders in S3
    For New Drives, List Segments
    Put them in Dynamo and Assign to a batch if not assigned already
    Add Drives until reaching max files allowed in 1 batch (hard limit of 10k)
    """
    # Establish AWS API Connections
    sts_client = boto3.client("sts")
    assumed_role_object = sts_client.assume_role(RoleArn=DAG_ROLE, RoleSessionName="AssumeRoleSession1")
    credentials = assumed_role_object["Credentials"]
    dynamodb = boto3.resource(
        "dynamodb",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )

    # Validate Config
    drives_to_process = kwargs["dag_run"].conf["drives_to_process"]
    example_input = {
        "drives_to_process": {
            "drive1": {
                "bucket": "addf-ros-image-demo-raw-bucket-d2be7d299",
                "prefix": "rosbag-scene-detection/drive1/",
            },
            "drive2": {"bucket": "addf-ros-image-demo-raw-bucket-d2be7d29", "prefix": "rosbag-scene-detection/drive2/"},
        }
    }

    for k, v in drives_to_process.items():
        assert isinstance(k, str), f"expecting config to be like {example_input}, received: {drives_to_process}"
        assert (
            "bucket" in v.keys() and "prefix" in v.keys()
        ), f"expecting config to be like {example_input}, received: {drives_to_process}"
        assert v["prefix"][-1] == "/"

    table = dynamodb.Table(DYNAMODB_TABLE)
    batch_id = kwargs["dag_run"].run_id

    files_in_batch = table.query(
        KeyConditionExpression=Key("pk").eq(batch_id),
        Select="COUNT",
    )["Count"]

    if files_in_batch > 0:
        print("Batch Id already exists in tracking table - using existing batch")
        return files_in_batch

    print("New Batch Id - collecting unprocessed drives from S3 and adding to the batch")
    files_in_batch = batch_creation_and_tracking.add_drives_to_batch(
        table=table,
        drives_to_process=drives_to_process,
        batch_id=batch_id,
        file_suffix=FILE_SUFFIX,
        s3_client=s3_client,
    )
    return files_in_batch


def get_job_queue_name() -> str:
    """get_job_queue_name retrieves the the available JobQueues created
    based on the inputs of the batch-compute manifest file.
    """
    return eval(f"{PROVIDER}_JOB_QUEUE_ARN")


def get_job_name() -> str:
    v = "".join(random.choice(string.ascii_lowercase) for i in range(6))
    return f"ros-image-pipeline-{v}"


def get_job_def_name() -> str:
    return f"addf-{DEPLOYMENT_NAME}-{MODULE_NAME}-jobdef"


def get_batch_client() -> BatchClient:
    sts_client = boto3.client("sts")

    response = sts_client.assume_role(
        RoleArn=DAG_ROLE,
        RoleSessionName="AssumeRoleSession1",
    )

    session = Session(
        aws_access_key_id=response["Credentials"]["AccessKeyId"],
        aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
        aws_session_token=response["Credentials"]["SessionToken"],
    )
    return session.client("batch")


def register_job_definition_on_demand(ti, job_def_name: str) -> str:
    client = get_batch_client()

    container_properties = {
        "image": f"{account}.dkr.ecr.{REGION}.amazonaws.com/{ECR_REPO_NAME}:rostopng",
        "jobRoleArn": DAG_ROLE,
        "environment": [
            {
                "name": "AWS_DEFAULT_REGION",
                "value": REGION,
            }
        ],
        "resourceRequirements": [
            {"value": VCPU, "type": "VCPU"},
            {"value": MEMORY, "type": "MEMORY"},
        ],
    }
    if PROVIDER == "FARGATE":
        container_properties["executionRoleArn"] = DAG_ROLE

    resp = client.register_job_definition(
        jobDefinitionName=job_def_name,
        type="container",
        containerProperties=container_properties,
        propagateTags=True,
        timeout={"attemptDurationSeconds": CONTAINER_TIMEOUT},
        retryStrategy={
            "attempts": 1,
        },
        platformCapabilities=[PROVIDER if PROVIDER in ["EC2", "FARGATE"] else "EC2"],
    )
    ti.xcom_push(key=TASK_DEF_XCOM_KEY, value=resp["jobDefinitionArn"])


def deregister_job_definition(ti, job_def_arn: str) -> None:
    client = get_batch_client()
    response = client.deregister_job_definition(jobDefinition=get_job_def_name())
    ti.xcom_push(key="TASK_DEF_DEREGISTER_XCOM_KEY", value=response["ResponseMetadata"])


with DAG(
    dag_id=DAG_ID,
    default_args=DEFAULT_ARGS,
    dagrun_timeout=timedelta(hours=2),
    start_date=days_ago(1),  # type: ignore
    schedule_interval="@once",
    render_template_as_native_obj=True,
) as dag:

    job_definition_name = get_job_def_name()
    job_name = get_job_name()
    queue_name = get_job_queue_name()

    create_aws_conn = PythonOperator(
        task_id="try_create_aws_conn",
        python_callable=try_create_aws_conn,
        dag=dag,
    )

    create_batch_of_drives_task = PythonOperator(
        task_id="create_batch_of_drives_task",
        python_callable=create_batch_of_drives,
        dag=dag,
        provide_context=True,
    )

    register_batch_job_defintion = PythonOperator(
        task_id="register-batch-job-definition",
        dag=dag,
        provide_context=True,
        python_callable=register_job_definition_on_demand,
        op_kwargs={"job_def_name": job_definition_name},
    )

    def batch_operation(**kwargs):
        ti = kwargs["ti"]
        ds = kwargs["ds"]
        array_size = ti.xcom_pull(task_ids="create_batch_of_drives_task", key="return_value")
        batch_id = kwargs["dag_run"].run_id

        if isinstance(array_size, dict):
            array_size = array_size["files_in_batch"]

        op = AwsBatchOperator(
            task_id="submit_batch_job_op",
            job_name=job_name,
            job_queue=queue_name,
            aws_conn_id="aws_default",
            job_definition=get_job_def_name(),
            array_properties={"size": int(array_size)},
            overrides={
                "command": [
                    "bash",
                    "-c",
                    textwrap.dedent(
                        """\
                            #/usr/bin/env bash
                            echo "Starting ROS"
                            source /opt/ros/noetic/setup.bash
                            export PYTHONPATH=$PYTHONPATH:$ROS_PACKAGE_PATH
                            env
                            
                            echo "[$(date)] Start Image Extraction - batch $BATCH_ID, index: $AWS_BATCH_JOB_ARRAY_INDEX"
                            python3 rostopng/main.py \
                                --tablename $TABLE_NAME \
                                --index $AWS_BATCH_JOB_ARRAY_INDEX \
                                --batchid $BATCH_ID \
                                --localbagpath $LOCAL_BAG_PATH \
                                --localimagespath $LOCAL_IMAGES_PATH \
                                --imagetopics $IMAGE_TOPICS \
                                --desiredencoding $DESIRED_ENCODING \
                                --targetbucket $TARGET_BUCKET \
                                --targetprefix $TARGET_PREFIX
                            """
                    ),
                ],
                "environment": [
                    {"name": "TABLE_NAME", "value": DYNAMODB_TABLE},
                    {"name": "BATCH_ID", "value": batch_id},
                    {"name": "JOB_NAME", "value": batch_id},
                    {"name": "DEBUG", "value": "true"},
                    {
                        "name": "AWS_ACCOUNT_ID",
                        "value": boto3.client("sts").get_caller_identity().get("Account"),
                    },
                    {"name": "LOCAL_BAG_PATH", "value": "/tmp/input.bag"},
                    {"name": "LOCAL_IMAGES_PATH", "value": "/tmp/images/"},
                    {"name": "LOCAL_VIDEO_PATH", "value": "/tmp/output.mp4"},
                    {"name": "IMAGE_TOPICS", "value": json.dumps(IMAGE_TOPICS)},
                    {"name": "DESIRED_ENCODING", "value": DESIRED_ENCODING},
                    {"name": "TARGET_BUCKET", "value": TARGET_BUCKET},
                ],
            },
        )

        op.execute(ds)

    submit_batch_job = PythonOperator(task_id="submit_batch_job", python_callable=batch_operation)

    def sagemaker_yolo_operation(**kwargs):

        # Establish AWS API Connections
        sts_client = boto3.client("sts")
        assumed_role_object = sts_client.assume_role(RoleArn=DAG_ROLE, RoleSessionName="AssumeRoleSession1")
        credentials = assumed_role_object["Credentials"]
        dynamodb = boto3.resource(
            "dynamodb",
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )
        table = dynamodb.Table(DYNAMODB_TABLE)
        batch_id = kwargs["dag_run"].run_id

        # Get Image Directories per Recording File to Label
        image_directory_items = table.query(
            KeyConditionExpression=Key("pk").eq(batch_id),
            Select="SPECIFIC_ATTRIBUTES",
            ProjectionExpression="raw_image_dirs"
        )['Items']

        image_directories = []
        for item in image_directory_items:
            image_directories += item['raw_image_dirs']

        logger.info(f"Starting object detection job for {len(image_directories)} directories")

        processor = Processor(
            image_uri=f"{account}.dkr.ecr.{REGION}.amazonaws.com/{ECR_REPO_NAME}:yolo",
            role=DAG_ROLE,
            instance_count=1,
            instance_type=YOLO_INSTANCE_TYPE,
            base_job_name=f"YOLO"
        )

        for image_directory in image_directories:
            logger.info(f"Starting object detection job for {image_directory}")
            logger.info(
                "Job details available at: "
                f"https://{REGION}.console.aws.amazon.com/sagemaker/home?region={REGION}#/processing-jobs"
            )
            processor.run(
                inputs=[
                    ProcessingInput(
                        input_name='data',
                        source=f"s3://{TARGET_BUCKET}/{image_directory}/",
                        destination='/opt/ml/processing/input/')
                ],
                outputs=[
                    ProcessingOutput(
                        output_name='output',
                        source='/opt/ml/processing/output/',
                        destination=f"s3://{TARGET_BUCKET}/{image_directory}_post_obj_dets/"
                    )
                ],
                arguments=['--model', MODEL],
                wait=False,
                logs=False,
            )

        logger.info("Waiting on all jobs to finish")
        logger.info(f"Jobs: {processor.jobs}")
        for job in processor.jobs:
            logger.info(f"Waiting on: {job} - logs from job:")
            job.wait(logs=True)

        logger.info(f"All object detection jobs complete")


    submit_yolo_job = PythonOperator(task_id="submit_yolo_job", python_callable=sagemaker_yolo_operation)

    deregister_batch_job_definition = PythonOperator(
        task_id="deregister_batch_job_definition",
        dag=dag,
        provide_context=True,
        op_kwargs={"job_def_arn": get_job_def_name()},
        python_callable=deregister_job_definition,
    )

    (
        create_aws_conn
        >> create_batch_of_drives_task
        >> register_batch_job_defintion
        >> submit_batch_job
        >> deregister_batch_job_definition
        >> submit_yolo_job
    )
