# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
import random
import string
from datetime import timedelta
from typing import Any, Dict, Iterator, List, TypeVar

import boto3
from airflow import DAG
from airflow.exceptions import AirflowFailException
from airflow.models.taskinstance import TaskInstance
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from boto3.session import Session
from mypy_boto3_sqs.client import SQSClient

from training_dags import dag_config
from training_dags.eks_job_operator import EksJobOperator

ValueType = TypeVar("ValueType")

DAG_ID = os.path.basename(__file__).replace(".py", "")

DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["airflow@example.com"],
}

logger = logging.getLogger("airflow")
logger.setLevel("DEBUG")


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


def fail_if_job_failed(ti: TaskInstance, eks_job_task_id: str) -> None:
    status = ti.xcom_pull(task_ids=eks_job_task_id, key="status")
    print(f"eks_job_task_id: {eks_job_task_id}  status: {status}")
    if status != "JOB_COMPLETED":
        raise AirflowFailException("EKS Job Failed")


def delete_queue(ti: TaskInstance, create_queue_task_id: str) -> None:
    client = get_client()
    url = ti.xcom_pull(task_ids=create_queue_task_id)
    client.delete_queue(QueueUrl=url)


def get_job_body(create_queue_task_id: str, parallelism: int, completions: int, max_failures: int) -> Dict[str, Any]:
    worker_pod_body = json.dumps(
        {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {},
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
                        "args": ["--url", "$(QUEUE_URL)", "--dir", "$(DIR)", "--single-message"],
                        "env": [
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
            },
        }
    )

    return {
        "apiVerson": "batch/v1",
        "kind": "Job",
        "metadata": {
            "labels": {"app": "addf-job"},
        },
        "spec": {
            "parallelism": 1,
            "completions": 1,
            "backoffLimit": 6,
            "template": {
                "metadata": {
                    "labels": {"app": "addf-job"},
                },
                "spec": {
                    "serviceAccountName": dag_config.MODULE_NAME,
                    "restartPolicy": "Never",
                    "priorityClassName": "system-node-critical",
                    "containers": [
                        {
                            "name": "pod-launcher",
                            "image": dag_config.SIMULATION_MOCK_IMAGE,
                            "command": ["kopf", "run"],
                            "args": [
                                "simulation_mock/pod_launcher.py",
                                "--namespace",
                                dag_config.EKS_NAMESPACE,
                                # "--verbose"
                            ],
                            "resources": {
                                "requests": {"memory": "512Mi", "cpu": "1"},
                                "limits": {"memory": "1Gi", "cpu": "1"},
                            },
                            "env": [
                                {"name": "NAMESPACE", "value": dag_config.EKS_NAMESPACE},
                                {
                                    "name": "POD_LAUNCHER_NAME",
                                    "valueFrom": {"fieldRef": {"fieldPath": "metadata.name"}},
                                },
                                {"name": "POD_LAUNCHER_UID", "valueFrom": {"fieldRef": {"fieldPath": "metadata.uid"}}},
                                {
                                    "name": "JOB_NAME",
                                    "valueFrom": {"fieldRef": {"fieldPath": "metadata.labels['job-name']"}},
                                },
                                {
                                    "name": "JOB_UID",
                                    "valueFrom": {"fieldRef": {"fieldPath": "metadata.labels['controller-uid']"}},
                                },
                                {"name": "PARALLELISM", "value": f"{parallelism}"},
                                {"name": "COMPLETIONS", "value": f"{completions}"},
                                {"name": "MAX_FAILURES", "value": f"{max_failures}"},
                                {"name": "AWS_DEFAULT_REGION", "value": dag_config.REGION},
                                {"name": "AWS_ACCOUNT_ID", "value": dag_config.ACCOUNT_ID},
                                {
                                    "name": "QUEUE_URL",
                                    "value": f"{{{{ ti.xcom_pull(task_ids='{create_queue_task_id}') }}}}",
                                },
                                {"name": "WORKER_POD_BODY", "value": worker_pod_body},
                            ],
                        },
                    ],
                },
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
    max_failures = 5

    create_queue_task = PythonOperator(
        task_id="create-queue",
        dag=dag,
        provide_context=True,
        python_callable=create_and_populate_queue,
        op_kwargs={"num_items": total_simulations},
    )

    job_task = EksJobOperator(
        task_id="coarse-fan-out-mock",
        dag=dag,
        namespace=dag_config.EKS_NAMESPACE,  # type: ignore
        body=get_job_body(
            create_queue_task_id=create_queue_task.task_id,
            parallelism=parallelism,
            completions=total_simulations,
            max_failures=max_failures,
        ),
        delete_policy="Never",
        cluster_name=dag_config.EKS_CLUSTER_NAME,  # type: ignore
        service_account_role_arn=dag_config.EKS_SERVICE_ACCOUNT_ROLE,  # type: ignore
        get_logs=True,
    )

    fail_if_job_failed_task = PythonOperator(
        task_id="fail-if-job-failed",
        dag=dag,
        provide_context=True,
        python_callable=fail_if_job_failed,
        op_kwargs={"eks_job_task_id": job_task.task_id},
    )

    delete_queue_task = PythonOperator(
        task_id="delete-queue",
        dag=dag,
        provide_context=True,
        python_callable=delete_queue,
        op_kwargs={"create_queue_task_id": create_queue_task.task_id},
    )

    create_queue_task >> job_task >> fail_if_job_failed_task >> delete_queue_task
