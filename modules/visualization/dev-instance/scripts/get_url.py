# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

#!/usr/bin/env python3

# type: ignore

import json
import sys
from argparse import ArgumentParser

import boto3


def main():
    parser = ArgumentParser(description="Request a Presigned URL from the generateUrlLambda")
    parser.add_argument(
        "--config-file",
        dest="config_file",
        required=False,
        help='Name of the JSON file with Module\'s Metadata, use "-" to read from STDIN',
    )
    parser.add_argument(
        "--bucket-name",
        dest="bucket_name",
        required=False,
        help="the name of the bucket containing rosbag file, required if no --config-file is provided",
    )
    parser.add_argument(
        "--function-name",
        dest="function_name",
        required=False,
        help="The generateUrlFunctionName, required if no --config-file is provided",
    )
    parser.add_argument("--key", dest="object_key", required=False, help="the key of the object in s3")
    parser.add_argument(
        "--record", dest="record_id", required=False, help="the partition key of the scene in the scenario db"
    )
    parser.add_argument("--scene", dest="scene_id", required=False, help="the sort key of the scene in the scenario db")
    args = parser.parse_args()

    if args.config_file is not None:
        if args.config_file == "-":
            metadata = json.load(sys.stdin)
        else:
            with open(args.config_file) as metadata_file:
                metadata = json.load(metadata_file)
    else:
        metadata = {}

    bucket_name = args.bucket_name if args.bucket_name is not None else metadata.get("TargetBucketName", None)
    if bucket_name is None:
        raise Exception('One of JSON config file key "TargetBucketName" or --bucket-name must be provided')

    function_name = (
        args.function_name if args.function_name is not None else metadata.get("GenerateUrlLambdaName", None)
    )
    if function_name is None:
        raise Exception('One of JSON config file key "GenerateUrlLambdaName" or --function-name must be provided')

    if args.object_key is None and (args.record_id is None or args.scene_id is None):
        raise Exception("You need to either specify --key or --record and --scene")

    client = boto3.client("lambda")
    print(f"Invoking: {function_name}")
    payload = {"bucket": bucket_name, "key": args.object_key, "record_id": args.record_id, "scene_id": args.scene_id}
    print("payload: " + json.dumps(payload))
    response = client.invoke(
        FunctionName=str(function_name), InvocationType="RequestResponse", LogType="Tail", Payload=json.dumps(payload)
    )

    res = json.loads(response["Payload"].read())
    statusCode = int(res.get("statusCode"))
    body = json.loads(res.get("body"))

    print(str(statusCode))
    if statusCode == 200:
        url = body.get("url")
        print(url)
    else:
        print(json.dumps(body))


if __name__ == "__main__":
    main()
