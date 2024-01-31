# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import sys

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger("emrserverless")
logger.setLevel("DEBUG")


def get_drive_files(src_bucket, src_prefix, file_suffix, s3_client):
    """For a given bucket, prefix, and suffix, lists all files found on S3 and returns a list of the files."""
    MAX_KEYS = 1000
    logger.info(src_bucket)
    logger.info(src_prefix)
    file_response = s3_client.list_objects_v2(Bucket=src_bucket, Prefix=src_prefix, MaxKeys=MAX_KEYS, Delimiter="/")
    logger.info(file_response)
    file_next_continuation = file_response.get("NextContinuationToken")
    files = [x["Key"] for x in file_response.get("Contents", []) if x["Key"].endswith(file_suffix)]
    while file_next_continuation is not None:
        file_response = s3_client.list_objects_v2(
            Bucket=src_bucket,
            Prefix=src_prefix,
            MaxKeys=MAX_KEYS,
            Delimiter="/",
            ContinuationToken=file_next_continuation,
        )
        file_next_continuation = file_response.get("NextContinuationToken")
        files += [x["Key"] for x in file_response.get("Contents", [])]
        logger.info(files)
    return files


def batch_write_files_to_dynamo(table, drives_and_files, batch_id):
    with table.batch_writer() as batch:
        idx = 0
        for drive_id, files in drives_and_files.items():
            for file in files["files"]:
                item = {
                    "drive_id": drive_id,
                    "file_id": file.split("/")[-1],
                    "s3_bucket": files["bucket"],
                    "s3_key": file,
                    "pk": batch_id,
                    "sk": str(idx),
                }
                logger.info(item)
                batch.put_item(Item=item)
                idx += 1


def add_drives_to_batch(
    table: str,
    batch_id: str,
    drives_to_process: dict[str, dict],
    file_suffix: str,
    s3_client: boto3.client,
):
    """Lists files with file_suffix for each prefix in drives_to_process and adds each file to dynamodb for tracking.

    @param table: dynamo tracking table
    @param batch_id: dag run id
    @param drives_to_process: {
        "drives_to_process": {
            "drive1": {"bucket": "addf-example-dev-raw-bucket-xyz", "prefix": "rosbag-scene-detection/drive1/"},
            "drive2": {"bucket": "addf-example-dev-raw-bucket-xyz", "prefix": "rosbag-scene-detection/drive2/"},
        },
    }
    @param file_suffix: ".bag"
    @param s3_client: type boto3.client('s3')
    @return:
    """

    drives_and_files = {}
    files_in_batch = 0
    for drive_id, s3_path in drives_to_process.items():
        files = get_drive_files(
            src_bucket=s3_path["bucket"],
            src_prefix=s3_path["prefix"],
            file_suffix=file_suffix,
            s3_client=s3_client,
        )

        drives_and_files[drive_id] = {"files": files, "bucket": s3_path["bucket"]}
        files_in_batch += len(files)
        logger.info(f"files_in_batch {files_in_batch}")

    batch_write_files_to_dynamo(table, drives_and_files, batch_id)
    return files_in_batch


def main() -> None:
    drives_to_process = kwargs["dag_run"].conf["drives_to_process"]
    batch_id = kwargs["dag_run"].run_id

    # Establish AWS API Connections
    dynamodb = boto3.resource("dynamodb")
    s3_client = boto3.client("s3")

    # Validate Config
    validate_config(drives_to_process)

    table = dynamodb.Table(DYNAMODB_TABLE)

    files_in_batch = table.query(
        KeyConditionExpression=Key("pk").eq(batch_id),
        Select="COUNT",
    )["Count"]

    if files_in_batch > 0:
        logger.info("Batch Id already exists in tracking table - using existing batch")
        return files_in_batch

    logger.info("New Batch Id - collecting unprocessed drives from S3 and adding to the batch")
    files_in_batch = add_drives_to_batch(
        table=table,
        drives_to_process=drives_to_process,
        batch_id=batch_id,
        file_suffix=FILE_SUFFIX,
        s3_client=s3_client,
    )
    assert files_in_batch <= 10000, "AWS Batch Array Size cannot exceed 10000"
    return files_in_batch


if __name__ == "__main__":
    main()
