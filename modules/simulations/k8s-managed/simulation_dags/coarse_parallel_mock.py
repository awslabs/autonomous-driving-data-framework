# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import random
import string
from datetime import timedelta
from typing import Any, Dict, Iterator, List, TypeVar

import boto3
from airflow import DAG
from airflow.models.taskinstance import TaskInstance
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from boto3.session import Session
from mypy_boto3_sqs.client import SQSClient

from simulation_dags import dag_config
from simulation_dags.eks_job_operator import EksJobOperator

ValueType = TypeVar("ValueType")

DAG_ID = os.path.basename(__file__).replace(".py", "")

DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["airflow@example.com"],
}

logger = logging.getLogger("airflow")
logger.setLevel("WARNING")


def get_client() -> SQSClient:
    sts_client = boto3.client("sts")

    response = sts_client.assume_role(
        RoleArn=dag_config.DAG_ROLE,
        RoleSessionName="AssumeRoleSession1",
    )

    session = Session(
        aws_access_key_id=response["Credentials"]["AccessKeyId"],
        aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
        aws_session_token=response["Credentials"]["SessionToken"],
    )

    return session.client("sqs")


def create_and_populate_queue(num_items: int) -> str:
    client = get_client()
    response = client.create_queue(
        QueueName=(
            f"addf-{dag_config.DEPLOYMENT_NAME}-{dag_config.MODULE_NAME}-"
            f"{''.join(random.choices(string.ascii_letters + string.digits, k=6))}"
        )
    )
    queue_url = response["QueueUrl"]

    def chunks(lst: List[ValueType], n: int) -> Iterator[ValueType]:
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    for i, chunk in enumerate(chunks(range(num_items), 10)):
        entries = [{"Id": str(j), "MessageBody": f"message-{i}-{j}-{value}"} for j, value in enumerate(chunk)]
        client.send_message_batch(QueueUrl=queue_url, Entries=entries)

    return queue_url


def delete_queue(ti: TaskInstance, create_queue_task_id: str) -> None:
    client = get_client()
    url = ti.xcom_pull(task_ids=create_queue_task_id)
    client.delete_queue(QueueUrl=url)


def get_job_body(create_queue_task_id: str, parallelism: int, completions: int) -> Dict[str, Any]:
    return {
        "apiVerson": "batch/v1",
        "kind": "Job",
        "metadata": {},
        "spec": {
            "parallelism": parallelism,
            "completions": completions,
            "backoffLimit": 6,
            "template": {
                "spec": {
                    "serviceAccountName": dag_config.MODULE_NAME,
                    "restartPolicy": "Never",
                    "volumes": [{"name": "shared-data", "emptyDir": {}}],
                    "containers": [
                        {
                            "name": "sqs-manager",
                            "image": dag_config.SIMULATION_MOCK_IMAGE,
                            "volumeMounts": [{"name": "shared-data", "mountPath": "/shared-data"}],
                            "command": ["python", "/var/simulation-mock/simulation_mock/sqs_manager.py"],
                            "args": ["--url", "$(URL)", "--dir", "$(DIR)", "--single-message"],
                            "env": [
                                {
                                    "name": "URL",
                                    "value": f"{{{{ ti.xcom_pull(task_ids='{create_queue_task_id}') }}}}",
                                },
                                {"name": "DIR", "value": "/shared-data"},
                                {"name": "DEBUG", "value": "true"},
                                {"name": "AWS_DEFAULT_REGION", "value": dag_config.REGION},
                                {"name": "AWS_ACCOUNT_ID", "value": dag_config.ACCOUNT_ID},
                            ],
                            "livenessProbe": {
                                "exec": {
                                    "command": ["cat", "/tmp/container.running"],
                                },
                                "initialDelaySeconds": 5,
                                "periodSeconds": 5,
                            },
                        },
                        {
                            "name": "simulator",
                            "image": dag_config.SIMULATION_MOCK_IMAGE,
                            "volumeMounts": [{"name": "shared-data", "mountPath": "/shared-data"}],
                            "command": ["python", "/var/simulation-mock/simulation_mock/simulator.py"],
                            "args": [
                                "--dir",
                                "$(DIR)",
                                "--max-seconds",
                                "$(MAX_SECONDS)",
                                "--failure-seed",
                                "$(FAILURE_SEED)",
                            ],
                            "env": [
                                {"name": "DIR", "value": "/shared-data"},
                                {"name": "MAX_SECONDS", "value": "60"},
                                # probability of failure = 1/FAILURE_SEED if 1 <= FAILURE_SEED <= 32768 else 0
                                {"name": "FAILURE_SEED", "value": "32769"},
                                {"name": "DEBUG", "value": "true"},
                                {"name": "AWS_DEFAULT_REGION", "value": dag_config.REGION},
                                {"name": "AWS_ACCOUNT_ID", "value": dag_config.ACCOUNT_ID},
                            ],
                            "livenessProbe": {
                                "exec": {
                                    "command": ["cat", "/tmp/container.running"],
                                },
                                "initialDelaySeconds": 5,
                                "periodSeconds": 5,
                            },
                        },
                    ],
                }
            },
        },
    }


with DAG(
    dag_id=DAG_ID,
    default_args=DEFAULT_ARGS,
    dagrun_timeout=timedelta(hours=6),
    start_date=days_ago(1),  # type: ignore
    schedule_interval="@once",
) as dag:

    total_simulations = 50
    parallelism = 10

    create_queue_task = PythonOperator(
        task_id="create-queue",
        dag=dag,
        provide_context=True,
        python_callable=create_and_populate_queue,
        op_kwargs={"num_items": total_simulations},
    )

    job_task = EksJobOperator(
        task_id="coarse-parallel-mock",
        dag=dag,
        namespace=dag_config.EKS_NAMESPACE,  # type: ignore
        body=get_job_body(
            create_queue_task_id=create_queue_task.task_id, parallelism=parallelism, completions=total_simulations
        ),
        delete_policy="IfSucceeded",
        cluster_name=dag_config.EKS_CLUSTER_NAME,  # type: ignore
        service_account_role_arn=dag_config.EKS_SERVICE_ACCOUNT_ROLE,  # type: ignore
        get_logs=False,
    )

    delete_queue_task = PythonOperator(
        task_id="delete_queue",
        dag=dag,
        provide_context=True,
        python_callable=delete_queue,
        op_kwargs={"create_queue_task_id": create_queue_task.task_id},
    )

    create_queue_task >> job_task >> delete_queue_task
