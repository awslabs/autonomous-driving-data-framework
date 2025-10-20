# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from datetime import date
from typing import Any, Dict

import boto3
import requests
from requests_aws4auth import AWS4Auth

region = os.getenv("REGION", "")
service = "es"
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    region,
    service,
    session_token=credentials.token,
)

host = os.getenv("DOMAIN_ENDPOINT", "")
index = "rosbag-metadata-scene-search"
type = "_doc"

headers = {"Content-Type": "application/json"}


def get_url() -> str:
    ts = date.today()
    return f"https://{host}/{index}-{ts}/{type}/"


def process_doc(records: Dict[Any, Any], doc: Dict[Any, Any]) -> None:
    for key, value in records.items():
        for param, val in value.items():
            doc[key] = val


def handler(event, _context) -> str:
    count = 0
    for record in event["Records"]:
        id_p = record["dynamodb"]["Keys"]["scene_id"]["S"]
        if record["eventName"] != "REMOVE":
            doc = {}
            doc["scene_id"] = id_p
            doc["bag_file"] = record["dynamodb"]["Keys"]["bag_file"]["S"]
            document = record["dynamodb"]["NewImage"]
            process_doc(records=document, doc=doc)
            try:
                requests.put(get_url() + id_p, auth=awsauth, json=doc, headers=headers, timeout=30)
            except requests.exceptions.InvalidURL:
                print("Error invoking endpoint - InvalidURL")
                raise requests.exceptions.InvalidURL
            except KeyError:
                print("Could not process the payload")
        count += 1
    return str(count) + " records processed."
