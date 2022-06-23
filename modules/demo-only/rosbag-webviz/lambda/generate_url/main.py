# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import os
from urllib.parse import quote_plus

import boto3
from botocore.config import Config
from botocore.errorfactory import ClientError

webviz_elb_url = os.environ["WEBVIZ_ELB_URL"]
dynamo_region = os.environ["SCENE_DB_REGION"]
dynamo_table_name = os.environ["SCENE_DB_TABLE"]
partition_key = os.environ["SCENE_DB_PARTITION_KEY"]
sort_key = os.environ["SCENE_DB_SORT_KEY"]
lambda_region = os.environ["AWS_REGION"]

bucket_key_ddb_name = "bag_file_bucket"
object_key_ddb_name = "bag_file_prefix"
start_time_ddb_name = "start_time"

dynamo_resource = boto3.resource("dynamodb", region_name=dynamo_region)
dynamo_table = dynamo_resource.Table(dynamo_table_name)


def query_scenes(record_id, scene_id):
    response = dynamo_table.get_item(Key={partition_key: record_id, sort_key: scene_id})
    return response["Item"]


def exists(s3, bucket, key):
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


def get_url(bucket, key, region, seek_to):
    region_config = Config(region_name=region)
    s3 = boto3.client("s3", config=region_config)
    if exists(s3, bucket, key):
        response = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=129600,
        )
        double_encoded = quote_plus(response)
        url = f"{webviz_elb_url}?remote-bag-url={double_encoded}"
        if seek_to is not None:
            url = f"{url}&seek-to={seek_to}"
        return url
    else:
        raise Exception(f"Could not find bag file s3://{bucket}/{key}")


def json_response(statusCode, content):
    return {"statusCode": statusCode, "body": json.dumps(content)}


def lambda_handler(event, context):
    try:
        record_id = event.get("record_id")
        scene_id = event.get("scene_id")
        seek_to = event.get("seek_to")
        bucket = event.get("bucket")
        key = event.get("key")
        region = event.get("region", lambda_region)

        if record_id is not None and scene_id is not None:
            scene = query_scenes(record_id, scene_id)
            try:
                bucket = scene[bucket_key_ddb_name]
                key = scene[object_key_ddb_name]
                seek_to = scene[start_time_ddb_name]
            except KeyError as ke:
                raise Exception(f"Could not find record field for {record_id}:{scene_id} in dynamo: {ke}")

        if bucket is None:
            return json_response(400, {"error": "No bucket specified"})

        if key is None:
            return json_response(400, {"error": "No key specified"})

        return json_response(200, {"url": get_url(bucket, key, region, seek_to)})
    except Exception as e:
        return json_response(500, {"error": str(e)})
