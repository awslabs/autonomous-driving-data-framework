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
from airflow.utils.dates import days_ago
from boto3.dynamodb.conditions import Key
from boto3.session import Session
from demo_dags import batch_creation_and_tracking
from demo_dags.dag_config import (
    CONTAINER_TIMEOUT,
    DAG_ROLE,
    DEPLOYMENT_NAME,
    DYNAMODB_TABLE,
    ECR_REPO_NAME,
    FARGATE_JOB_QUEUE_ARN,
    FILE_SUFFIX,
    MAX_NUM_FILES_PER_BATCH,
    MEMORY,
    MODULE_NAME,
    ON_DEMAND_JOB_QUEUE_ARN,
    PROVIDER,
    REGION,
    SPOT_JOB_QUEUE_ARN,
    SRC_BUCKET,
    TARGET_BUCKET,
    VCPU,
)
from mypy_boto3_batch.client import BatchClient

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
        conn = Connection(
            conn_id=conn_id, conn_type="aws", host="", schema="", login="", extra=extra
        )
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
    sts_client = boto3.client("sts")
    assumed_role_object = sts_client.assume_role(
        RoleArn=DAG_ROLE, RoleSessionName="AssumeRoleSession1"
    )
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

    table = dynamodb.Table(DYNAMODB_TABLE)
    batch_id = kwargs["dag_run"].run_id

    files_in_batch = table.query(
        KeyConditionExpression=Key("pk").eq(batch_id),
        Select="COUNT",
    )["Count"]

    if files_in_batch > 0:
        print("Batch Id already exists in tracking table - using existing batch")
        return files_in_batch

    print(
        "New Batch Id - collecting unprocessed drives from S3 and adding to the batch"
    )
    files_in_batch = 0
    while True:
        print(f"Segments in Batch: {files_in_batch}")
        next_continuation = None
        (
            files_in_batch,
            next_continuation,
        ) = batch_creation_and_tracking.add_drives_to_batch(
            table,
            SRC_BUCKET,
            MAX_NUM_FILES_PER_BATCH,
            batch_id,
            files_in_batch=files_in_batch,
            next_continuation=None if files_in_batch == 0 else next_continuation,
            file_suffix=FILE_SUFFIX,
            s3_client=s3_client,
        )
        if next_continuation is None or files_in_batch > MAX_NUM_FILES_PER_BATCH:
            print(f"Final Batch Size = {files_in_batch} files")
            return files_in_batch


def get_job_queue_name() -> str:
    """get_job_queue_name retrieves the the available JobQueues created
    based on the inputs of the batch-compute manifest file.
    """
    return eval(f"{PROVIDER}_JOB_QUEUE_ARN")


def get_job_name() -> str:
    v = "".join(random.choice(string.ascii_lowercase) for i in range(6))
    return f"batch_simple_mock-{v}"


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
    region = REGION
    account = boto3.client("sts").get_caller_identity().get("Account")

    container_properties = {
        "image": f"{account}.dkr.ecr.{region}.amazonaws.com/{ECR_REPO_NAME}:latest",
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

    def my_func(**kwargs):
        ti = kwargs["ti"]
        ds = kwargs["ds"]
        array_size = ti.xcom_pull(
            task_ids="create_batch_of_drives_task", key="return_value"
        )
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
                            echo "[$(date)] Start $JOB_NAME for batch $BATCH_ID and index: $AWS_BATCH_JOB_ARRAY_INDEX"

                            echo "Getting file from Dynamo for batch $BATCH_ID and index: $AWS_BATCH_JOB_ARRAY_INDEX"

                            python processing_mock/processing.py --tablename $TABLE_NAME \
                                --s3bucketout $TARGET_BUCKET \
                                --index $AWS_BATCH_JOB_ARRAY_INDEX --batchid $BATCH_ID

                            """
                    ),
                ],
                "environment": [
                    {"name": "BATCH_ID", "value": batch_id},
                    {"name": "TABLE_NAME", "value": DYNAMODB_TABLE},
                    {"name": "JOB_NAME", "value": batch_id},
                    {"name": "DEBUG", "value": "true"},
                    {
                        "name": "AWS_ACCOUNT_ID",
                        "value": boto3.client("sts")
                        .get_caller_identity()
                        .get("Account"),
                    },
                    {"name": "TARGET_BUCKET", "value": TARGET_BUCKET},
                ],
            },
        )

        op.execute(ds)

    submit_batch_job = PythonOperator(
        task_id="submit_batch_job", python_callable=my_func
    )

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
    )
