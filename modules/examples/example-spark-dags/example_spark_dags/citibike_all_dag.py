"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import json
import random
import string
import zipfile
from datetime import datetime, timedelta
from io import BytesIO

import boto3
from airflow import DAG, settings
from airflow.contrib.hooks.aws_hook import AwsHook
from airflow.exceptions import AirflowException
from airflow.models import Connection
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.providers.amazon.aws.operators.emr_containers import EMRContainerOperator
from airflow.providers.amazon.aws.sensors.emr_containers import EMRContainerSensor
from boto3.session import Session

from example_spark_dags import emr_eks_dag_config

afbucket = f"{emr_eks_dag_config.DAG_BUCKET}/dags/example_spark_dags/"  # ADDF MWAA Dags bucket
emr_virtual_cluster_id = emr_eks_dag_config.VIRTUAL_CLUSTER_ID
emr_execution_role_arn = emr_eks_dag_config.EMR_JOB_EXECUTION_ROLE
YR = "2020"
bucket = emr_eks_dag_config.RAW_BUCKET  # ADDF RAW bucket
SRC_BUCKET = "tripdata"
SRC_KEY = "-citibike-tripdata.csv.zip"
DEST_BUCKET = emr_eks_dag_config.RAW_BUCKET
DEST_KEY = "-citibike-tripdata.csv"

now = datetime.now()


def try_create_aws_conn(**kwargs):
    conn_id = "aws_emr_on_eks"
    try:
        AwsHook.get_connection(conn_id)
    except AirflowException:
        extra = json.dumps({"role_arn": emr_eks_dag_config.DAG_ROLE}, indent=2)
        conn = Connection(conn_id=conn_id, conn_type="aws", host="", schema="", login="", extra=extra)
        try:
            session = settings.Session()
            session.add(conn)
            session.commit()
        finally:
            session.close()


def get_assumerole_creds():
    sts_client = boto3.client("sts")

    response = sts_client.assume_role(
        RoleArn=emr_eks_dag_config.DAG_ROLE,
        RoleSessionName="AssumeRoleSession",
    )

    session = Session(
        aws_access_key_id=response["Credentials"]["AccessKeyId"],
        aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
        aws_session_token=response["Credentials"]["SessionToken"],
    )
    return session


def find_max_month():
    session = get_assumerole_creds()
    conn = session.client("s3")
    mo = 0
    for key in conn.list_objects(Bucket=SRC_BUCKET)["Contents"]:
        if "JC" not in key["Key"] and YR in key["Key"]:
            mo = mo + 1
    print("returning max month {}".format(mo))
    return mo


def copy_and_unzip_s3(**context):
    session = get_assumerole_creds()
    s3_resource = session.resource("s3")
    zip_obj = s3_resource.Object(bucket_name=context["bucket"], key=context["key"])
    buffer = BytesIO(zip_obj.get()["Body"].read())
    z = zipfile.ZipFile(buffer)
    print("downloaded zip {}, zipObj {}".format(z, zipfile))
    for filename in z.namelist():
        if filename.startswith("__"):
            continue
        file_info = z.getinfo(filename)
        print("interating over zip {}, zipObj {}".format(filename, file_info))
        try:
            response = s3_resource.meta.client.upload_fileobj(
                z.open(filename), Bucket=context["destbucket"], Key=context["destkey"]
            )
            print("uploaded to s3 {}".format(filename))
        except Exception as e:
            print(e)


def list_bucket(**context):
    session = get_assumerole_creds()
    conn = session.client("s3")
    for key in conn.list_objects(Bucket=context["destbucket"])["Contents"]:
        if "csv.gz" in key["Key"]:
            print(key["Key"])


DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["airflow@example.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 5,
    "retry_delay": timedelta(minutes=1),
}

# [START howto_operator_emr_containers_start_job_run]
JOB_DRIVER = {
    "sparkSubmitJobDriver": {
        "entryPoint": "s3://" + afbucket + "citibike-spark-all.py",
        "entryPointArguments": [bucket],
        "sparkSubmitParameters": "--conf spark.executor.instances=3 --conf "
        "spark.executor.memory=4G --conf spark.driver.memory=2G --conf spark.executor.cores=2 "
        "--conf spark.sql.shuffle.partitions=60 --conf spark.dynamicAllocation.enabled=false",
    }
}

CONFIGURATION_OVERRIDES = {
    "monitoringConfiguration": {
        "cloudWatchMonitoringConfiguration": {
            "logGroupName": "/emr-containers/jobs",
            "logStreamNamePrefix": "addf",
        },
        "persistentAppUI": "ENABLED",
        "s3MonitoringConfiguration": {"logUri": "s3://" + afbucket + "/joblogs"},
    }
}

with DAG(
    dag_id="Citibike_Ridership_Analytics",
    default_args=DEFAULT_ARGS,
    dagrun_timeout=timedelta(hours=2),
    start_date=datetime(now.year, now.month, now.day, now.hour),
    schedule_interval=None,
    tags=["S3", "Citibike", "EMR on EKS", "Spark"],
) as dag:
    start = DummyOperator(task_id="start", dag=dag)

    listBucket = PythonOperator(
        task_id="list_transformed_files",
        python_callable=list_bucket,
        op_kwargs={"destbucket": DEST_BUCKET},
        dag=dag,
    )

    create_aws_conn = PythonOperator(
        task_id="try_create_aws_conn",
        python_callable=try_create_aws_conn,
        dag=dag,
    )

    for i in range(1, find_max_month() + 1):
        NEW_SRC_KEY = YR + str(i).zfill(2) + SRC_KEY
        NEW_DEST_KEY = "citibike/csv/" + YR + str(i).zfill(2) + DEST_KEY
        copyAndTransformS3File = PythonOperator(
            task_id="copy_and_unzip_s3_" + str(i).zfill(2),
            python_callable=copy_and_unzip_s3,
            op_kwargs={
                "bucket": SRC_BUCKET,
                "key": NEW_SRC_KEY,
                "destbucket": DEST_BUCKET,
                "destkey": NEW_DEST_KEY,
            },
            dag=dag,
        )

        start >> copyAndTransformS3File >> listBucket

        start_job_run = EMRContainerOperator(
            task_id=f"start_citibike_ridership_analytics-{i}",
            name="citibike_analytics_run",
            virtual_cluster_id=emr_virtual_cluster_id,
            client_request_token="".join(random.choice(string.digits) for _ in range(10)),
            execution_role_arn=emr_execution_role_arn,
            release_label="emr-6.2.0-latest",
            job_driver=JOB_DRIVER,
            configuration_overrides=CONFIGURATION_OVERRIDES,
            aws_conn_id="aws_emr_on_eks",
        )

        job_sensor = EMRContainerSensor(
            task_id=f"check_job_status-{i}",
            job_id="{{ task_instance.xcom_pull(task_ids='start_citibike_ridership_analytics', key='return_value') }}",
            virtual_cluster_id="{{ task_instance.xcom_pull(task_ids='start_citibike_ridership_analytics', key='virtual_cluster_id') }}",
            aws_conn_id="aws_emr_on_eks",
        )

        create_aws_conn >> listBucket >> start_job_run >> job_sensor
