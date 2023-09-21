# conftest.py
import os
import random

import boto3
import moto
import pytest
from moto.server import ThreadedMotoServer

WD = os.getcwd()
MODULE_PATH = "modules/analysis/rosbag-image-pipeline"
if MODULE_PATH not in WD:
    WD = f"{WD}/{MODULE_PATH}"
DAG_CONFIG_PATH = f"{WD}/image_dags/dag_config.py"
DAG_CONFIG_BACKUP_PATH = f"{WD}/image_dags/dag_config.bak"


def pytest_configure(config):
    """
    Allows plugins and conftest files to perform initial configuration.
    This hook is called for every plugin and initial conftest
    file after command line options have been parsed.
    """
    os.rename(DAG_CONFIG_PATH, DAG_CONFIG_BACKUP_PATH)
    sample_data = """ADDF_MODULE_METADATA = '{"PrivateSubnetIds":["subnet-090a22976151932d7","subnet-0d0f12bd07e5ed4ea","subnet-011bad0900787e44e"],"DagId":"vsi_image_pipeline","SecurityGroupId":"sg-08460867be55fd219","DagRoleArn":"arn:aws:iam::1234567890:role/addf-aws-solutions-analysis-rip-dag-us-east-1","DynamoDbTableName":"addf-aws-solutions-analysis-rip-drive-tracking","DetectionsDynamoDBName":"addf-aws-solutions-core-metadata-storage-Rosbag-Scene-Metadata","SourceBucketName":"addf-aws-solutions-raw-bucket-074ff5b4","TargetBucketName":"addf-aws-solutions-intermediate-bucket-074ff5b4","DagBucketName":"addf-aws-solutions-artifacts-bucket-074ff5b4","LogsBucketName":"addf-aws-solutions-logs-bucket-074ff5b4","OnDemandJobQueueArn":"arn:aws:batch:us-east-1:1234567890:job-queue/addf-aws-solutions-core-batch-compute-OnDemandJobQueue","SpotJobQueueArn":"arn:aws:batch:us-east-1:1234567890:job-queue/addf-aws-solutions-core-batch-compute-SpotJobQueue","FargateJobQueueArn":"arn:aws:batch:us-east-1:1234567890:job-queue/addf-aws-solutions-core-batch-compute-FargateJobQueue","ParquetBatchJobDefArn":"arn:aws:batch:us-east-1:1234567890:job-definition/addf-aws-solutions-docker-images-ros-to-parquet:1","PngBatchJobDefArn":"arn:aws:batch:us-east-1:1234567890:job-definition/addf-aws-solutions-docker-images-ros-to-png:1","ObjectDetectionImageUri":"1234567890.dkr.ecr.us-east-1.amazonaws.com/addf-aws-solutions-docker-images-object-detection:latest","ObjectDetectionRole":"arn:aws:iam::1234567890:role/addf-aws-solutions-docker-addfawssolutionsdockerim-1WI5F9LEEAN39","ObjectDetectionJobConcurrency":30,"ObjectDetectionInstanceType":"ml.m5.xlarge","LaneDetectionImageUri":"1234567890.dkr.ecr.us-east-1.amazonaws.com/addf-aws-solutions-docker-images-lane-detection:smprocessor","LaneDetectionRole":"arn:aws:iam::1234567890:role/addf-aws-solutions-docker-addfawssolutionsdockerim-1U2OPJ0QGMLSM","LaneDetectionJobConcurrency":20,"LaneDetectionInstanceType":"ml.m5.2xlarge","FileSuffix":".bag","DesiredEncoding":"bgr8","YoloModel":"yolov5s","ImageTopics":["/flir_adk/rgb_front_left/image_raw","/flir_adk/rgb_front_right/image_raw"],"SensorTopics":["/vehicle/gps/fix","/vehicle/gps/time","/vehicle/gps/vel","/imu_raw"]}'
DEPLOYMENT_NAME = 'aws-solutions'
MODULE_NAME = 'analysis-rip'
REGION = 'us-east-1'
EMR_JOB_EXECUTION_ROLE = 'arn:aws:iam::1234567890:role/addf-aws-solutions-core-e-addfawssolutionscoreemrs-KNO49U56R3MO'
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
    os.rename(DAG_CONFIG_BACKUP_PATH, DAG_CONFIG_PATH)

@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
    os.environ["MOTO_ACCOUNT_ID"] = "123456789012"

@pytest.fixture(scope="function")
def moto_dynamodb(aws_credentials):
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
def moto_s3(aws_credentials):
    with moto.mock_s3():
        s3 = boto3.client("s3")
        try:
            s3.create_bucket(
                Bucket="mybucket",
                CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
            )
        except Exception as e:
            print(f"bucket creation failed: {e}")
        yield s3


@pytest.fixture(scope="function")
def moto_server():
    port = random.randint(5001, 8999)
    server = ThreadedMotoServer(port=port)
    server.start()
    yield port
    server.stop()
