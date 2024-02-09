# conftest.py
import os
import random

import boto3
import moto
import pytest
from moto.server import ThreadedMotoServer

WD = os.getcwd()
MODULE_PATH = "modules/analysis/rosbag-image-pipeline-sfn"
if MODULE_PATH not in WD:
    WD = f"{WD}/{MODULE_PATH}"


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
