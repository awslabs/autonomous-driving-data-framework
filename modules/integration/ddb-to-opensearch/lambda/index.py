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


def get_url():
    ts = date.today()
    return f"https://{host}/{index}-{ts}/{type}/"


def handler(event, context):
    count = 0
    for record in event["Records"]:
        id = record["dynamodb"]["Keys"]["scene_id"]["S"]
        if not record["eventName"] == "REMOVE":
            doc = {}
            doc["scene_id"] = id
            doc["bag_file"] = record["dynamodb"]["Keys"]["bag_file"]["S"]
            document = record["dynamodb"]["NewImage"]
            for key, value in document.items():
                for param, val in value.items():
                    doc[key] = val
            _ = requests.put(get_url() + id, auth=awsauth, json=doc, headers=headers)
        count += 1
    return str(count) + " records processed."
