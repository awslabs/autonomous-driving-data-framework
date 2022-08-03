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
import time
from datetime import timedelta
from math import ceil
from typing import TypeVar

import boto3
from airflow import DAG, settings
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.exceptions import AirflowException
from airflow.models import Connection
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.batch import AwsBatchOperator
from airflow.utils.dates import days_ago
from airflow.utils.task_group import TaskGroup
from boto3.dynamodb.conditions import Key
from sagemaker.processing import ProcessingInput, ProcessingOutput, Processor
from sagemaker.pytorch.processing import PyTorchProcessor

from image_dags import batch_creation_and_tracking
from image_dags.dag_config import ADDF_MODULE_METADATA, DEPLOYMENT_NAME, MODULE_NAME, REGION

# SET VARIABLES FOR EXTRACTION
PROVIDER = "FARGATE"  # One of ON_DEMAND, SPOT, FARGATE
FILE_SUFFIX = ".bag"
IMAGE_TOPICS = [
    "/flir_adk/rgb_front_left/image_raw",
    "/flir_adk/rgb_front_right/image_raw",
]
SENSOR_TOPICS = [
    "/vehicle/gps/fix",
    "/vehicle/gps/time",
    "/vehicle/gps/vel",
    "/imu_raw",
]
DESIRED_ENCODING = "bgr8"

# SET VARIABLES FOR OBJECT DETECTION
MODEL = "yolov5s"

# GET MODULE VARIABLES FROM APP.PY AND DEPLOYSPEC
addf_module_metadata = json.loads(ADDF_MODULE_METADATA)
DAG_ROLE = addf_module_metadata["DagRoleArn"]
DYNAMODB_TABLE = addf_module_metadata["DynamoDbTableName"]
FARGATE_JOB_QUEUE_ARN = addf_module_metadata["FargateJobQueueArn"]
ON_DEMAND_JOB_QUEUE_ARN = addf_module_metadata["OnDemandJobQueueArn"]
SPOT_JOB_QUEUE_ARN = addf_module_metadata["SpotJobQueueArn"]
TARGET_BUCKET = addf_module_metadata["TargetBucketName"]
PNG_JOB_DEFINITION_ARN = addf_module_metadata["PngBatchJobDefArn"]
PARQUET_JOB_DEFINITION_ARN = addf_module_metadata["ParquetBatchJobDefArn"]
YOLO_IMAGE_URI = addf_module_metadata["ObjectDetectionImageUri"]
YOLO_ROLE = addf_module_metadata["ObjectDetectionRole"]
YOLO_CONCURRENCY = addf_module_metadata["ObjectDetectionJobConcurrency"]
YOLO_INSTANCE_TYPE = addf_module_metadata["ObjectDetectionInstanceType"]


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


def validate_config(drives_to_process):
    example_input = {
        "drives_to_process": {
            "drive2": {
                "bucket": "addf-ros-image-demo-raw-bucket-d2be7d29",
                "prefix": "rosbag-scene-detection/drive2/",
            },
        }
    }

    for k, v in drives_to_process.items():
        assert isinstance(k, str), f"expecting config to be like {example_input}, received: {drives_to_process}"
        assert (
            "bucket" in v.keys() and "prefix" in v.keys()
        ), f"expecting config to be like {example_input}, received: {drives_to_process}"
        assert v["prefix"][-1] == "/"


def create_batch_of_drives(ti, **kwargs):
    """
    if Batch Id already exists, then run dag again on exact same files
    Else:
        List Drive Folders in S3
        For New Drives, List Recording Files
        Put New Drives and Recording Files in Dynamo and Assign to a batch if not assigned already
        Add Drives until reaching max files allowed in 1 batch (hard limit of 10k)
    """
    drives_to_process = kwargs["dag_run"].conf["drives_to_process"]
    batch_id = kwargs["dag_run"].run_id
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

    validate_config(drives_to_process)

    table = dynamodb.Table(DYNAMODB_TABLE)

    files_in_batch = table.query(
        KeyConditionExpression=Key("pk").eq(batch_id),
        Select="COUNT",
    )["Count"]

    if files_in_batch > 0:
        logger.info("Batch Id already exists in tracking table - using existing batch")
        return files_in_batch

    logger.info("New Batch Id - collecting unprocessed drives from S3 and adding to the batch")
    files_in_batch = batch_creation_and_tracking.add_drives_to_batch(
        table=table,
        drives_to_process=drives_to_process,
        batch_id=batch_id,
        file_suffix=FILE_SUFFIX,
        s3_client=s3_client,
    )
    assert files_in_batch <= 10000, "AWS Batch Array Size cannot exceed 10000"
    return files_in_batch


def get_job_queue_name() -> str:
    """get_job_queue_name retrieves the the available JobQueues created
    based on the inputs of the batch-compute manifest file.
    """
    return eval(f"{PROVIDER}_JOB_QUEUE_ARN")


def get_job_name(suffix="") -> str:
    v = "".join(random.choice(string.ascii_lowercase) for i in range(6))
    return f"ros-image-pipeline-{suffix}-{v}"


def png_batch_operation(**kwargs):
    ti = kwargs["ti"]
    ds = kwargs["ds"]
    array_size = ti.xcom_pull(task_ids="create-batch-of-drives", key="return_value")
    batch_id = kwargs["dag_run"].run_id

    op = AwsBatchOperator(
        task_id="submit_batch_job_op",
        job_name=get_job_name("png"),
        job_queue=queue_name,
        aws_conn_id="aws_default",
        job_definition=PNG_JOB_DEFINITION_ARN,
        array_properties={"size": int(array_size)},
        overrides={
            "environment": [
                {"name": "TABLE_NAME", "value": DYNAMODB_TABLE},
                {"name": "BATCH_ID", "value": batch_id},
                {"name": "DEBUG", "value": "true"},
                {"name": "IMAGE_TOPICS", "value": json.dumps(IMAGE_TOPICS)},
                {"name": "DESIRED_ENCODING", "value": DESIRED_ENCODING},
                {"name": "TARGET_BUCKET", "value": TARGET_BUCKET},
            ],
        },
    )

    op.execute(ds)


def parquet_operation(**kwargs):
    ti = kwargs["ti"]
    ds = kwargs["ds"]
    array_size = ti.xcom_pull(task_ids="create-batch-of-drives", key="return_value")
    batch_id = kwargs["dag_run"].run_id

    op = AwsBatchOperator(
        task_id="submit_parquet_job_op",
        job_name=get_job_name("parq"),
        job_queue=queue_name,
        aws_conn_id="aws_default",
        job_definition=PARQUET_JOB_DEFINITION_ARN,
        array_properties={"size": int(array_size)},
        overrides={
            "environment": [
                {"name": "TABLE_NAME", "value": DYNAMODB_TABLE},
                {"name": "BATCH_ID", "value": batch_id},
                {"name": "TOPICS", "value": json.dumps(SENSOR_TOPICS)},
                {"name": "TARGET_BUCKET", "value": TARGET_BUCKET},
            ],
        },
    )

    op.execute(ds)


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
        ProjectionExpression="raw_image_dirs",
    )["Items"]

    image_directories = []
    for item in image_directory_items:
        image_directories += item["raw_image_dirs"]

    logger.info(f"Starting object detection job for {len(image_directories)} directories")

    total_jobs = len(image_directories)
    num_batches = ceil(total_jobs / YOLO_CONCURRENCY)

    for i in range(num_batches):
        logger.info(f"Starting object detection job for batch {i + 1} of {num_batches}")
        processor = Processor(
            image_uri=YOLO_IMAGE_URI,
            role=YOLO_ROLE,
            instance_count=1,
            instance_type=YOLO_INSTANCE_TYPE,
            base_job_name=f"{batch_id.replace(':', '').replace('_', '')[0:23]}-YOLO",
        )

        idx_start = i * YOLO_CONCURRENCY
        idx_end = (i + 1) * YOLO_CONCURRENCY
        for image_directory in image_directories[idx_start:idx_end]:
            logger.info(f"Starting object detection job for {image_directory}")
            logger.info(
                "Job details available at: "
                f"https://{REGION}.console.aws.amazon.com/sagemaker/home?region={REGION}#/processing-jobs"
            )
            processor.run(
                inputs=[
                    ProcessingInput(
                        input_name="data",
                        source=f"s3://{TARGET_BUCKET}/{image_directory}/",
                        destination="/opt/ml/processing/input/",
                    )
                ],
                outputs=[
                    ProcessingOutput(
                        output_name="output",
                        source="/opt/ml/processing/output/",
                        destination=f"s3://{TARGET_BUCKET}/{image_directory}_post_obj_dets/",
                    )
                ],
                arguments=["--model", MODEL],
                wait=False,
                logs=False,
            )
            time.sleep(1)  # Attempt at avoiding throttling exceptions

        logger.info("Waiting on batch of jobs to finish")
        for job in processor.jobs:
            logger.info(f"Waiting on: {job} - logs from job:")
            job.wait(logs=False)

        logger.info("All object detection jobs complete")


with DAG(
    dag_id=DAG_ID,
    default_args=DEFAULT_ARGS,
    dagrun_timeout=timedelta(hours=2),
    start_date=days_ago(1),  # type: ignore
    schedule_interval="@once",
    render_template_as_native_obj=True,
) as dag:

    queue_name = get_job_queue_name()

    create_aws_conn = PythonOperator(
        task_id="try-create-aws-conn",
        python_callable=try_create_aws_conn,
        dag=dag,
    )

    create_batch_of_drives_task = PythonOperator(
        task_id="create-batch-of-drives",
        python_callable=create_batch_of_drives,
        dag=dag,
        provide_context=True,
    )

    # Start Task Group definition
    with TaskGroup(group_id="sensor-extraction") as extract_task_group:

        submit_png_job = PythonOperator(task_id="image-extraction-batch-job", python_callable=png_batch_operation)
        submit_parquet_job = PythonOperator(task_id="parquet-extraction-batch-job", python_callable=parquet_operation)
        create_batch_of_drives_task >> [submit_parquet_job, submit_png_job]

    with TaskGroup(group_id="image-labelling") as image_labelling_task_group:
        submit_yolo_job = PythonOperator(
            task_id="object-detection-sagemaker-job",
            python_callable=sagemaker_yolo_operation,
        )
        submit_lane_det_job = DummyOperator(task_id="lane-detection-sagemaker-job")

    create_aws_conn >> create_batch_of_drives_task >> extract_task_group
    submit_png_job >> image_labelling_task_group
