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
def moto_server():
    port = random.randint(5001, 8999)
    server = ThreadedMotoServer(port=port)
    server.start()
    yield port
    server.stop()
