#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License").
#    You may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import os
from datetime import date

import boto3
import requests
from requests_aws4auth import AWS4Auth

region = os.getenv("REGION", "")
service = "es"
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

host = os.getenv("DOMAIN_ENDPOINT", "")
index = "rosbag-metadata-scene-search"
type = "_doc"

headers = {"Content-Type": "application/json"}


def get_url() -> str:
    ts = date.today()
    return f"https://{host}/{index}-{ts}/{type}/"


def handler(event, _context) -> str:
    count = 0
    for record in event["Records"]:
        id_p = record["dynamodb"]["Keys"]["scene_id"]["S"]
        if record["eventName"] != "REMOVE":
            doc = {}
            doc["scene_id"] = id_p
            doc["bag_file"] = record["dynamodb"]["Keys"]["bag_file"]["S"]
            document = record["dynamodb"]["NewImage"]
            for key, value in document.items():
                for param, val in value.items():
                    doc[key] = val
            try:
                requests.put(get_url() + id_p, auth=awsauth, json=doc, headers=headers)
            except requests.exceptions.InvalidURL:
                print("Error invoking endpoint - InvalidURL")
                raise requests.exceptions.InvalidURL
            except KeyError:
                print("Could not process the payload")
        count += 1
    return str(count) + " records processed."
