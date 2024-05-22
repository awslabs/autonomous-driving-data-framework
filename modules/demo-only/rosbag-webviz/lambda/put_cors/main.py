# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3

cors_rule = {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "ExposeHeaders": ["ETag", "Content-Type", "Accept-Ranges", "Content-Length"],
    "MaxAgeSeconds": 3000,
}

s3 = boto3.client("s3")


def lambda_handler(event, context):
    print(event)
    bucket_name = event["ResourceProperties"]["bucket_name"]
    raw_bucket_name = event["ResourceProperties"]["raw_bucket_name"]
    allowed_origin = event["ResourceProperties"]["allowed_origin"]
    cors_rule["AllowedOrigins"] = [allowed_origin]
    if "https" not in allowed_origin:
        https_origin = allowed_origin.replace("http", "https")
        cors_rule["AllowedOrigins"].append(https_origin)
    cors_configuration = {"CORSRules": [cors_rule]}
    s3.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_configuration)
    s3.put_bucket_cors(Bucket=raw_bucket_name, CORSConfiguration=cors_configuration)
