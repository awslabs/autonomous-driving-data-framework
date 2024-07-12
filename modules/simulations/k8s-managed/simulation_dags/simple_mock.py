# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import textwrap
from datetime import timedelta

from airflow import DAG
from airflow.utils.dates import days_ago

from simulation_dags import dag_config
from simulation_dags.eks_job_operator import EksJobOperator

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
    envs = {"JOB_NAME": "Simple Mock", "MAX_SECONDS": "120", "FAILURE_SEED": "20"}

    default_delete_policy = "IfSucceeded"

    body = {
        "apiVerson": "batch/v1",
        "kind": "Job",
        "metadata": {},
        "spec": {
            "parallelism": 10,
            "completions": 50,
            "backoffLimit": 6,
            "template": {
                "spec": {
                    "restartPolicy": "OnFailure",
                    "containers": [
                        {
                            "name": "job-executor",
                            "image": "ubuntu",
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
                        }
                    ],
                }
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
