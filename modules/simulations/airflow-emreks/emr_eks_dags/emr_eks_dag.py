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
from typing import Iterator, List, TypeVar

import boto3
from airflow import DAG, settings
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.exceptions import AirflowException
from airflow.models import Connection
from airflow.models.taskinstance import TaskInstance
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.emr_containers import EMRContainerOperator
from airflow.utils.dates import days_ago
from boto3.session import Session

from emr_eks_dags import emr_eks_dag_config

ValueType = TypeVar("ValueType")

DAG_ID = os.path.basename(__file__).replace(".py", "")

# Airflow Args
DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["airflow@example.com"],
}
CONN_ID = "aws_batch"

# emr parameters
EMR_RELEASE_LABEL = "emr-6.5.0-latest"
EMR_IMAGE_URI = os.getenv("AIRFLOW__CORE__EMR_IMAGE_URI")
EMR_EKS_JOB_EXECUTION_ROLE_ARN = os.getenv(
    "AIRFLOW__CORE__EMR_EKS_JOB_EXECUTION_ROLE_ARN"
)
EMR_VIRTUAL_CLUSTER_ID = os.getenv("AIRFLOW__CORE__EMR_VIRTUAL_CLUSTER_ID")

logger = logging.getLogger("airflow")
logger.setLevel("DEBUG")


def try_create_aws_conn(**kwargs):
    try:
        AwsHook.get_connection(CONN_ID)
    except AirflowException:
        extra = json.dumps({"role_arn": emr_eks_dag_config.DAG_ROLE}, indent=2)
        conn = Connection(
            CONN_ID=CONN_ID, conn_type="aws", host="", schema="", login="", extra=extra
        )
        try:
            session = settings.Session()
            session.add(conn)
            session.commit()
        finally:
            session.close()


# def get_batch_client() -> BatchClient:
#     sts_client = boto3.client("sts")

#     response = sts_client.assume_role(
#         RoleArn=emr_eks_dag_config.DAG_ROLE,
#         RoleSessionName="AssumeRoleSession1",
#     )

#     session = Session(
#         aws_access_key_id=response["Credentials"]["AccessKeyId"],
#         aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
#         aws_session_token=response["Credentials"]["SessionToken"],
#     )
#     return session.client("batch")


with DAG(
    dag_id=DAG_ID,
    default_args=DEFAULT_ARGS,
    dagrun_timeout=timedelta(hours=2),
    start_date=days_ago(1),  # type: ignore
    schedule_interval="@once",
) as dag:

    total_simulations = 50
    parallelism = 10

    JOB_DRIVER_ARG = {
        "sparkSubmitJobDriver": {
            "entryPoint": f"s3://{BI_ETL_SCRIPTS}/{ETL_SCRIPT_PATH[1]}",
            "entryPointArguments": [BI_DATA_LAKE_RAW, BI_DATA_LAKE_RAW_PREFIX[1]],
            "sparkSubmitParameters": "--conf spark.driver.memory=37G --conf spark.executors.memory=37G --conf spark.executor.cores=5 --conf spark.driver.cores=5",
        }
    }

    CONFIGURATION_OVERRIDES_ARG = {
        "applicationConfiguration": [
            {
                "classification": "spark-defaults",
                "properties": {
                    "spark.hadoop.hive.metastore.client.factory.class": "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory",
                    "spark.dynamicAllocation.enabled": "true",
                    "spark.dynamicAllocation.shuffleTracking.enabled": "true",
                    "spark.dynamicAllocation.minExecutors": "113",
                    "spark.dynamicAllocation.maxExecutors": "170",
                    "spark.dynamicAllocation.initialExecutors": "113",
                },
            }
        ],
        "monitoringConfiguration": {
            "cloudWatchMonitoringConfiguration": {
                "logGroupName": "/aws/emr-eks-spark",
                "logStreamNamePrefix": "airflow",
            }
        },
    }

    create_aws_conn = PythonOperator(
        task_id="try_create_aws_conn",
        python_callable=try_create_aws_conn,
        dag=dag,
    )

    trigger_emroneks_job = EMRContainerOperator(
        task_id="Trigger-EMRonEKS-Job",
        virtual_cluster_id=EMR_VIRTUAL_CLUSTER_ID,
        execution_role_arn=EMR_EKS_JOB_EXECUTION_ROLE_ARN,
        release_label=EMR_RELEASE_LABEL,
        job_driver=JOB_DRIVER_ARG,
        configuration_overrides=CONFIGURATION_OVERRIDES_ARG,
        name="trigger_emroneks_job",
        aws_conn_id=CONN_ID,
        # retries=3
    )

    create_aws_conn >> trigger_emroneks_job
