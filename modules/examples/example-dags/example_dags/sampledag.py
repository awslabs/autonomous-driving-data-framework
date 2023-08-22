# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from datetime import timedelta

import boto3
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from boto3.session import Session

import example_dags.dag_config as cf

DAG_ID = os.path.basename(__file__).replace(".py", "")

DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["airflow@example.com"],
}


def triggerDagFn(**kwargs):
    sts_client = boto3.client("sts")

    # Call the assume_role method of the STSConnection object and pass the role
    # ARN and a role session name

    response = sts_client.assume_role(
        RoleArn=cf.DAG_ROLE,
        RoleSessionName="AssumeRoleSession1",
    )

    session = Session(
        aws_access_key_id=response["Credentials"]["AccessKeyId"],
        aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
        aws_session_token=response["Credentials"]["SessionToken"],
    )

    new_sts_client = session.client("sts")
    print(f"The new client is : {new_sts_client.get_caller_identity()}")

    ec2_client = session.client("ec2")
    response = ec2_client.describe_instances()
    print(f"response is: {response}")

    return True


with DAG(
    dag_id=DAG_ID,
    default_args=DEFAULT_ARGS,
    dagrun_timeout=timedelta(hours=2),
    start_date=days_ago(1),
    schedule_interval="@once",
) as dag:
    triggerDag = PythonOperator(task_id="triggerDag", python_callable=triggerDagFn, provide_context=True)
