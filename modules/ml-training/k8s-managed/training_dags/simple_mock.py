# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from datetime import timedelta

from airflow import DAG
from airflow.utils.dates import days_ago

from training_dags import dag_config
from training_dags.eks_job_operator import EksJobOperator

DAG_ID = os.path.basename(__file__).replace(".py", "")

DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["airflow@example.com"],
}

logger = logging.getLogger("airflow")
logger.setLevel("DEBUG")


with DAG(
    dag_id=DAG_ID,
    default_args=DEFAULT_ARGS,
    dagrun_timeout=timedelta(hours=2),
    start_date=days_ago(1),  # type: ignore
    schedule_interval="@once",
) as dag:
    # caller_identity = PythonOperator(task_id="log_caller_identity", dag=dag, python_callable=log_caller_identity)
    envs = {"JOB_NAME": "MNIST Lustre"}

    default_delete_policy = "IfSucceeded"

    body = {
        "apiVerson": "batch/v1",
        "kind": "Job",
        "metadata": {},
        "spec": {
            "backoffLimit": 1,
            "template": {
                "metadata": {"annotations": {"sidecar.istio.io/inject": "false"}},
                "spec": {
                    "restartPolicy": "OnFailure",
                    "containers": [
                        {
                            "name": "pytorch",
                            "image": dag_config.PYTORCH_IMAGE,
                            "imagePullPolicy": "Always",
                            "volumeMounts": [
                                {
                                    "name": "persistent-storage",
                                    "mountPath": "/data",
                                }
                            ],
                            "command": [
                                "python3",
                                "/aws/pytorch-mnist/mnist.py",
                                "--epochs=1",
                                "--save-model",
                            ],
                            "env": [],
                            # "resources": {"limits": {"nvidia.com/gpu": 1}},
                        }
                    ],
                    "nodeSelector": {"usage": "gpu"},
                    "volumes": [
                        {
                            "name": "persistent-storage",
                            "persistentVolumeClaim": {"claimName": dag_config.PVC_NAME},
                        }
                    ],
                },
            },
        },
    }

    job_task = EksJobOperator(
        task_id="bash-mock-job",
        dag=dag,
        namespace=dag_config.EKS_NAMESPACE,  # type: ignore
        envs=envs,
        body=body,
        delete_policy=default_delete_policy,
        cluster_name=dag_config.EKS_CLUSTER_NAME,  # type: ignore
        service_account_role_arn=dag_config.EKS_SERVICE_ACCOUNT_ROLE,  # type: ignore
    )

    job_task
