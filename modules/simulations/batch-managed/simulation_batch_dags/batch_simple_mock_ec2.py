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
from boto3.session import Session
from mypy_boto3_batch.client import BatchClient

from simulation_batch_dags import batch_dag_config

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


def try_create_aws_conn(**kwargs):
    conn_id = "aws_batch"
    try:
        AwsHook.get_connection(conn_id)
    except AirflowException:
        extra = json.dumps({"role_arn": batch_dag_config.DAG_ROLE}, indent=2)
        conn = Connection(conn_id=conn_id, conn_type="aws", host="", schema="", login="", extra=extra)
        try:
            session = settings.Session()
            session.add(conn)
            session.commit()
        finally:
            session.close()


def get_job_queue_name() -> str:
    """get_job_queue_name retrieves the the available JobQueues created
    based on the inputs of the batch-compute manifest file.
    """
    ON_DEMAND_JOB_QUEUE_ARN = batch_dag_config.ON_DEMAND_JOB_QUEUE_ARN  # consume if created
    # SPOT_JOB_QUEUE_ARN = batch_dag_config.SPOT_JOB_QUEUE_ARN  # consume if created
    # FARGATE_JOB_QUEUE_ARN = batch_dag_config.FARGATE_JOB_QUEUE_ARN  # consume if created

    return ON_DEMAND_JOB_QUEUE_ARN.split("/")[-1]


def get_job_name() -> str:
    v = "".join(random.choice(string.ascii_lowercase) for i in range(6))
    return f"addf-{batch_dag_config.DEPLOYMENT_NAME}-{batch_dag_config.MODULE_NAME}-simplemock-job-{v}"


def get_job_def_name() -> str:
    # v = "".join(random.choice(string.ascii_lowercase) for i in range(6))
    # return f"addf-{batch_dag_config.DEPLOYMENT_NAME}-{batch_dag_config.MODULE_NAME}-jobdef-{v}"
    return f"addf-{batch_dag_config.DEPLOYMENT_NAME}-{batch_dag_config.MODULE_NAME}-simplemock-jobdef"


def get_batch_client() -> BatchClient:
    sts_client = boto3.client("sts")

    response = sts_client.assume_role(
        RoleArn=batch_dag_config.DAG_ROLE,
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
    resp = client.register_job_definition(
        jobDefinitionName=job_def_name,
        type="container",
        containerProperties={
            "image": "ubuntu",
            "jobRoleArn": batch_dag_config.DAG_ROLE,
            "environment": [
                {
                    "name": "AWS_DEFAULT_REGION",
                    "value": batch_dag_config.REGION,
                }
            ],
            "resourceRequirements": [
                {"value": "1", "type": "VCPU"},
                {"value": "512", "type": "MEMORY"},
            ],
        },
        propagateTags=True,
        timeout={"attemptDurationSeconds": 60},
        platformCapabilities=["EC2"],
    )
    ti.xcom_push(key=TASK_DEF_XCOM_KEY, value=resp["jobDefinitionArn"])


def deregister_job_definition(ti, job_def_arn: str) -> None:
    client = get_batch_client()
    response = client.deregister_job_definition(jobDefinition=job_def_arn)
    ti.xcom_push(key="TASK_DEF_DEREGISTER_XCOM_KEY", value=response["ResponseMetadata"])


with DAG(
    dag_id=DAG_ID,
    default_args=DEFAULT_ARGS,
    dagrun_timeout=timedelta(hours=2),
    start_date=days_ago(1),  # type: ignore
    schedule_interval="@once",
) as dag:

    total_simulations = 50
    parallelism = 10

    job_definition_name = get_job_def_name()
    job_name = get_job_name()
    queue_name = get_job_queue_name()

    create_aws_conn = PythonOperator(
        task_id="try_create_aws_conn",
        python_callable=try_create_aws_conn,
        dag=dag,
    )

    register_batch_job_defintion = PythonOperator(
        task_id="register-batch-job-definition",
        dag=dag,
        provide_context=True,
        python_callable=register_job_definition_on_demand,
        op_kwargs={"job_def_name": job_definition_name},
    )

    submit_batch_job = AwsBatchOperator(
        task_id="submit_batch_job",
        job_name=job_name,
        job_queue=queue_name,
        aws_conn_id="aws_batch",
        # job_definition="{{ task_instance.xcom_pull(task_ids='register_batch_job_defintion', key='job_definition_name') }}", # noqa: E501
        job_definition="addf-local-simulations-batch-managed-simplemock-jobdef",  # TODO
        overrides={
            "command": [
                "bash",
                "-c",
                textwrap.dedent(
                    """\
                        #/usr/bin/env bash
                        echo "[$(date)] Starting $JOB_NAME"

                        TIC_COUNT=$RANDOM
                        let "TIC_COUNT %= $MAX_SECONDS"

                        FAILURE_CHECK=$RANDOM
                        let "FAILURE_CHECK %= $FAILURE_SEED"

                        echo "[$(date)] Random Runtime: $TIC_COUNT"
                        echo "[$(date)] Random Failure: $FAILURE_CHECK"

                        CURRENT_COUNT=0
                        while true; do
                            CURRENT_COUNT=$((CURRENT_COUNT + 1))
                            if [ "$CURRENT_COUNT" -ge "$TIC_COUNT" ]; then
                                break
                            fi
                            sleep 1
                        done

                        if [ "$FAILURE_CHECK" -eq "0" ]; then
                            echo "[$(date)] Failure" && exit 1
                        else
                            echo "[$(date)] Complete" && exit 0
                        fi
                        """
                ),
            ],
            "environment": [
                {"name": "JOB_NAME", "value": "Simple Batch Mock"},
                {"name": "MAX_SECONDS", "value": "120"},
                {"name": "FAILURE_SEED", "value": "20"},
                {"name": "DEBUG", "value": "true"},
                {"name": "AWS_ACCOUNT_ID", "value": batch_dag_config.ACCOUNT_ID},
            ],
        },
    )

    deregister_batch_job_defintion = PythonOperator(
        task_id="deregister_batch_job_defintion",
        dag=dag,
        provide_context=True,
        op_kwargs={
            # "job_def_arn": "{{ task_instance.xcom_pull(task_ids='deregister_batch_job_defintion', key='job_definition_arn') }}" # noqa: E501
            "job_def_arn": "addf-local-simulations-batch-managed-simplemock-jobdef"
        },
        python_callable=deregister_job_definition,
    )

    create_aws_conn >> register_batch_job_defintion >> submit_batch_job >> deregister_batch_job_defintion
