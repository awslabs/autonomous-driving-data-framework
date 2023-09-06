# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


import json
import logging
import os
import random
import string
import sys
import time
from datetime import timedelta
from math import ceil
from typing import TypeVar

import boto3
from airflow import DAG, settings
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.exceptions import AirflowException
from airflow.models import Connection
from airflow.operators.python import PythonOperator, get_current_context, task
from airflow.providers.amazon.aws.operators.batch import BatchOperator
from airflow.providers.amazon.aws.operators.emr import EmrServerlessStartJobOperator
from airflow.providers.amazon.aws.sensors.emr import EmrServerlessJobSensor
from airflow.utils.dates import days_ago
from airflow.utils.task_group import TaskGroup
from boto3.dynamodb.conditions import Key
from sagemaker.network import NetworkConfig
from sagemaker.processing import ProcessingInput, ProcessingOutput, Processor

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from batch_creation_and_tracking import add_drives_to_batch
from dag_config import (
    ADDF_MODULE_METADATA,
    DEPLOYMENT_NAME,
    EMR_APPLICATION_ID,
    EMR_JOB_EXECUTION_ROLE,
    MODULE_NAME,
    REGION,
    S3_SCRIPT_DIR,
)

# GET MODULE VARIABLES FROM APP.PY AND DEPLOYSPEC
addf_module_metadata = json.loads(ADDF_MODULE_METADATA)
DAG_ID = addf_module_metadata["DagId"]
DAG_ROLE = addf_module_metadata["DagRoleArn"]
DYNAMODB_TABLE = addf_module_metadata["DynamoDbTableName"]
FARGATE_JOB_QUEUE_ARN = addf_module_metadata["FargateJobQueueArn"]
ON_DEMAND_JOB_QUEUE_ARN = addf_module_metadata["OnDemandJobQueueArn"]
SPOT_JOB_QUEUE_ARN = addf_module_metadata["SpotJobQueueArn"]
TARGET_BUCKET = addf_module_metadata["TargetBucketName"]
FILE_SUFFIX = addf_module_metadata["FileSuffix"]

PRIVATE_SUBNETS_IDS = addf_module_metadata["PrivateSubnetIds"]
SM_SECURITY_GROUP_ID = addf_module_metadata["SecurityGroupId"]
PNG_JOB_DEFINITION_ARN = addf_module_metadata["PngBatchJobDefArn"]
DESIRED_ENCODING = addf_module_metadata["DesiredEncoding"]
IMAGE_TOPICS = addf_module_metadata["ImageTopics"]

PARQUET_JOB_DEFINITION_ARN = addf_module_metadata["ParquetBatchJobDefArn"]
SENSOR_TOPICS = addf_module_metadata["SensorTopics"]

YOLO_IMAGE_URI = addf_module_metadata["ObjectDetectionImageUri"]
YOLO_ROLE = addf_module_metadata["ObjectDetectionRole"]
YOLO_CONCURRENCY = addf_module_metadata["ObjectDetectionJobConcurrency"]
YOLO_INSTANCE_TYPE = addf_module_metadata["ObjectDetectionInstanceType"]
YOLO_MODEL = addf_module_metadata["YoloModel"]

LANEDET_IMAGE_URI = addf_module_metadata["LaneDetectionImageUri"]
LANEDET_ROLE = addf_module_metadata["LaneDetectionRole"]
LANEDET_CONCURRENCY = addf_module_metadata["LaneDetectionJobConcurrency"]
LANEDET_INSTANCE_TYPE = addf_module_metadata["LaneDetectionInstanceType"]

# EMR Config
# spark_app_dir = f"s3://{addf_module_metadata['DagBucketName']}/spark_jobs/"
# EMR_VIRTUAL_CLUSTER_ID = addf_module_metadata['EmrVirtualClusterId']
# EMR_JOB_ROLE_ARN = addf_module_metadata['EmrJobRoleArn']
# ARTIFACT_BUCKET = addf_module_metadata["DagBucketName"]
LOGS_BUCKET = addf_module_metadata["LogsBucketName"]
SCENE_TABLE = addf_module_metadata["DetectionsDynamoDBName"]

CONFIGURATION_OVERRIDES = {
    "monitoringConfiguration": {
        "managedPersistenceMonitoringConfiguration": {"enabled": True},
        "s3MonitoringConfiguration": {"logUri": f"s3://{LOGS_BUCKET}/scene-detection"},
    }
}

account = boto3.client("sts").get_caller_identity().get("Account")

ValueType = TypeVar("ValueType")

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
    files_in_batch = add_drives_to_batch(
        table=table,
        drives_to_process=drives_to_process,
        batch_id=batch_id,
        file_suffix=FILE_SUFFIX,
        s3_client=s3_client,
    )
    assert files_in_batch <= 10000, "AWS Batch Array Size cannot exceed 10000"
    return files_in_batch


def get_job_name(suffix="") -> str:
    v = "".join(random.choice(string.ascii_lowercase) for _i in range(6))
    return f"ros-image-pipeline-{suffix}-{v}"


def png_batch_operation(**kwargs):

    logger.info(f"kwargs at png_batch_operations is {kwargs}")

    ti = kwargs["ti"]
    ds = kwargs["ds"]
    array_size = ti.xcom_pull(task_ids="create-batch-of-drives", key="return_value")
    batch_id = kwargs["dag_run"].run_id
    context = get_current_context()

    op = BatchOperator(
        task_id="submit_batch_job_op",
        job_name=get_job_name("png"),
        job_queue=ON_DEMAND_JOB_QUEUE_ARN,
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

    # op.execute(ds)
    op.execute(context)


def parquet_operation(**kwargs):
    ti = kwargs["ti"]
    ds = kwargs["ds"]
    array_size = ti.xcom_pull(task_ids="create-batch-of-drives", key="return_value")
    batch_id = kwargs["dag_run"].run_id
    context = get_current_context()

    op = BatchOperator(
        task_id="submit_parquet_job_op",
        job_name=get_job_name("parq"),
        job_queue=FARGATE_JOB_QUEUE_ARN,
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

    op.execute(context)


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
        ProjectionExpression="resized_image_dirs",
    )["Items"]

    image_directories = []
    for item in image_directory_items:
        image_directories += item["resized_image_dirs"]

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
            network_config=NetworkConfig(subnets=PRIVATE_SUBNETS_IDS, security_group_ids=[SM_SECURITY_GROUP_ID]),
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
                arguments=["--model", YOLO_MODEL],
                wait=False,
                logs=False,
            )
            time.sleep(1)  # Attempt at avoiding throttling exceptions

        logger.info("Waiting on batch of jobs to finish")
        for job in processor.jobs:
            logger.info(f"Waiting on: {job} - logs from job:")
            job.wait(logs=False)

        logger.info("All object detection jobs complete")


def sagemaker_lanedet_operation(**kwargs):
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
        ProjectionExpression="resized_image_dirs",
    )["Items"]

    image_directories = []
    for item in image_directory_items:
        image_directories += item["resized_image_dirs"]

    logger.info(f"Starting lane detection job for {len(image_directories)} directories")

    total_jobs = len(image_directories)
    num_batches = ceil(total_jobs / LANEDET_CONCURRENCY)

    for i in range(num_batches):
        logger.info(f"Starting lane detection job for batch {i + 1} of {num_batches}")
        processor = Processor(
            image_uri=LANEDET_IMAGE_URI,
            role=LANEDET_ROLE,
            instance_count=1,
            instance_type=LANEDET_INSTANCE_TYPE,
            base_job_name=f"{batch_id.replace(':', '').replace('_', '')[0:23]}-LANE",
            network_config=NetworkConfig(subnets=PRIVATE_SUBNETS_IDS, security_group_ids=[SM_SECURITY_GROUP_ID]),
        )
        LOCAL_INPUT = "/opt/ml/processing/input/image"
        LOCAL_OUTPUT = "/opt/ml/processing/output/image"
        LOCAL_OUTPUT_JSON = "/opt/ml/processing/output/json"
        LOCAL_OUTPUT_CSV = "/opt/ml/processing/output/csv"

        idx_start = i * LANEDET_CONCURRENCY
        idx_end = (i + 1) * LANEDET_CONCURRENCY
        for image_directory in image_directories[idx_start:idx_end]:
            logger.info(f"Starting lane detection job for {image_directory}")
            logger.info(
                "Job details available at: "
                f"https://{REGION}.console.aws.amazon.com/sagemaker/home?region={REGION}#/processing-jobs"
            )
            processor.run(
                arguments=[
                    "--save_dir",
                    LOCAL_OUTPUT,
                    "--source",
                    LOCAL_INPUT,
                    "--json_path",
                    LOCAL_OUTPUT_JSON,
                    "--csv_path",
                    LOCAL_OUTPUT_CSV,
                ],
                inputs=[
                    ProcessingInput(
                        input_name="data",
                        source=f"s3://{TARGET_BUCKET}/{image_directory}/",
                        destination=LOCAL_INPUT,
                    )
                ],
                outputs=[
                    ProcessingOutput(
                        output_name="image_output",
                        source=LOCAL_OUTPUT,
                        destination=f"s3://{TARGET_BUCKET}/{image_directory}_post_lane_dets/",
                    ),
                    ProcessingOutput(
                        output_name="json_output",
                        source=LOCAL_OUTPUT_JSON,
                        destination=f"s3://{TARGET_BUCKET}/{image_directory}_post_lane_dets/",
                    ),
                    ProcessingOutput(
                        output_name="csv_output",
                        source=LOCAL_OUTPUT_CSV,
                        destination=f"s3://{TARGET_BUCKET}/{image_directory}_post_lane_dets/",
                    ),
                ],
                wait=False,
                logs=False,
            )
            time.sleep(1)  # Attempt at avoiding throttling exceptions

        logger.info("Waiting on batch of jobs to finish")
        for job in processor.jobs:
            logger.info(f"Waiting on: {job} - logs from job:")
            job.wait(logs=False)

        logger.info("All object detection jobs complete")


def emr_batch_operation(**kwargs):
    ds = kwargs["ds"]
    batch_id = kwargs["dag_run"].run_id

    JOB_DRIVER = {
        "sparkSubmit": {
            "entryPoint": f"{S3_SCRIPT_DIR}detect_scenes.py",
            "entryPointArguments": [
                "--batch-metadata-table-name",
                DYNAMODB_TABLE,
                "--batch-id",
                batch_id,
                "--output-bucket",
                TARGET_BUCKET,
                "--region",
                REGION,
                "--output-dynamo-table",
                SCENE_TABLE,
            ],
            "sparkSubmitParameters": f"--jars {S3_SCRIPT_DIR}spark-dynamodb_2.12-1.1.1.jar",
        }
    }

    start_job_run_op = EmrServerlessStartJobOperator(
        task_id="scene_detection",
        application_id=EMR_APPLICATION_ID,
        execution_role_arn=EMR_JOB_EXECUTION_ROLE,
        job_driver=JOB_DRIVER,
        configuration_overrides=CONFIGURATION_OVERRIDES,
        aws_conn_id="aws_default",
    )

    job_run_id = start_job_run_op.execute(ds)
    return job_run_id


with DAG(
    dag_id=DAG_ID,
    default_args=DEFAULT_ARGS,
    dagrun_timeout=timedelta(hours=2),
    start_date=days_ago(1),  # type: ignore
    schedule_interval="@once",
    render_template_as_native_obj=True,
) as dag:
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
        submit_lane_det_job = PythonOperator(
            task_id="lane-detection-sagemaker-job",
            python_callable=sagemaker_lanedet_operation,
        )

    with TaskGroup(group_id="scene-detection") as scene_detection_task_group:
        start_job_run = PythonOperator(task_id="scene-detection", python_callable=emr_batch_operation)

        job_sensor = EmrServerlessJobSensor(
            task_id=f"check-emr-job-status",
            application_id=EMR_APPLICATION_ID,
            job_run_id="{{ task_instance.xcom_pull(task_ids='scene-detection.scene-detection', key='return_value') }}",
            aws_conn_id="aws_default",
        )
        start_job_run >> job_sensor

    create_aws_conn >> create_batch_of_drives_task >> extract_task_group
    submit_png_job >> image_labelling_task_group >> scene_detection_task_group
