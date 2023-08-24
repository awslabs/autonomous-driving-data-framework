# conftest.py
import os
import random

import boto3
import json
import moto
import pytest
from moto.server import ThreadedMotoServer

DAG_CONFIG_PATH = "image_dags/dag_config.py"


def pytest_configure(config):
    """
    Allows plugins and conftest files to perform initial configuration.
    This hook is called for every plugin and initial conftest
    file after command line options have been parsed.
    """
    os.rename(DAG_CONFIG_PATH, "image_dags/dag_config.bak")
    sample_data = """ADDF_MODULE_METADATA = '{"PrivateSubnetIds":["subnet-090a22976151932d7","subnet-0d0f12bd07e5ed4ea","subnet-011bad0900787e44e"],"DagId":"vsi_image_pipeline","SecurityGroupId":"sg-08460867be55fd219","DagRoleArn":"arn:aws:iam::616260033377:role/addf-aws-solutions-analysis-rip-dag-us-east-1","DynamoDbTableName":"addf-aws-solutions-analysis-rip-drive-tracking","DetectionsDynamoDBName":"addf-aws-solutions-core-metadata-storage-Rosbag-Scene-Metadata","SourceBucketName":"addf-aws-solutions-raw-bucket-074ff5b4","TargetBucketName":"addf-aws-solutions-intermediate-bucket-074ff5b4","DagBucketName":"addf-aws-solutions-artifacts-bucket-074ff5b4","LogsBucketName":"addf-aws-solutions-logs-bucket-074ff5b4","OnDemandJobQueueArn":"arn:aws:batch:us-east-1:616260033377:job-queue/addf-aws-solutions-core-batch-compute-OnDemandJobQueue","SpotJobQueueArn":"arn:aws:batch:us-east-1:616260033377:job-queue/addf-aws-solutions-core-batch-compute-SpotJobQueue","FargateJobQueueArn":"arn:aws:batch:us-east-1:616260033377:job-queue/addf-aws-solutions-core-batch-compute-FargateJobQueue","ParquetBatchJobDefArn":"arn:aws:batch:us-east-1:616260033377:job-definition/addf-aws-solutions-docker-images-ros-to-parquet:1","PngBatchJobDefArn":"arn:aws:batch:us-east-1:616260033377:job-definition/addf-aws-solutions-docker-images-ros-to-png:1","ObjectDetectionImageUri":"616260033377.dkr.ecr.us-east-1.amazonaws.com/addf-aws-solutions-docker-images-object-detection:latest","ObjectDetectionRole":"arn:aws:iam::616260033377:role/addf-aws-solutions-docker-addfawssolutionsdockerim-1WI5F9LEEAN39","ObjectDetectionJobConcurrency":30,"ObjectDetectionInstanceType":"ml.m5.xlarge","LaneDetectionImageUri":"616260033377.dkr.ecr.us-east-1.amazonaws.com/addf-aws-solutions-docker-images-lane-detection:smprocessor","LaneDetectionRole":"arn:aws:iam::616260033377:role/addf-aws-solutions-docker-addfawssolutionsdockerim-1U2OPJ0QGMLSM","LaneDetectionJobConcurrency":20,"LaneDetectionInstanceType":"ml.m5.2xlarge","FileSuffix":".bag","DesiredEncoding":"bgr8","YoloModel":"yolov5s","ImageTopics":["/flir_adk/rgb_front_left/image_raw","/flir_adk/rgb_front_right/image_raw"],"SensorTopics":["/vehicle/gps/fix","/vehicle/gps/time","/vehicle/gps/vel","/imu_raw"]}'
DEPLOYMENT_NAME = 'aws-solutions'
MODULE_NAME = 'analysis-rip'
REGION = 'us-east-1'
EMR_JOB_EXECUTION_ROLE = 'arn:aws:iam::616260033377:role/addf-aws-solutions-core-e-addfawssolutionscoreemrs-KNO49U56R3MO'
EMR_APPLICATION_ID = '00fcldsv5ol5dv09'
S3_SCRIPT_DIR = 's3://addf-aws-solutions-artifacts-bucket-074ff5b4/dags/aws-solutions/analysis-rip/image_dags/'
    """

    # Writing to sample.json
    with open(DAG_CONFIG_PATH, "w") as outfile:
        outfile.write(sample_data)


def pytest_unconfigure(config):
    """
    called before test process is exited.
    """
    os.remove(DAG_CONFIG_PATH)
    os.rename("image_dags/dag_config.bak", DAG_CONFIG_PATH)


@pytest.fixture(scope="function")
def moto_dynamodb():
    with moto.mock_dynamodb():
        dynamodb = boto3.resource("dynamodb")
        dynamodb.create_table(
            TableName="mytable",
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "N"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield dynamodb


@pytest.fixture(scope="function")
def moto_s3():
    with moto.mock_s3():
        s3 = boto3.client("s3")
        s3.create_bucket(Bucket="mybucket")
        yield s3


@pytest.fixture(scope="function")
def moto_server():
    port = random.randint(5001, 8999)
    server = ThreadedMotoServer(port=port)
    server.start()
    yield port
    server.stop()
