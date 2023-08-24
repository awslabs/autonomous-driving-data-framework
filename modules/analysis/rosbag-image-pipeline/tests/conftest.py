# conftest.py
import os
import random

import boto3
import moto
import pytest
from moto.server import ThreadedMotoServer


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
