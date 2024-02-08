import logging
import os
import typing

import boto3
from boto3.dynamodb.conditions import Key

if typing.TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource
    from mypy_boto3_s3.client import S3Client


logger = logging.getLogger()
logger.setLevel("DEBUG")

dynamodb_resource = boto3.resource("dynamodb")
s3_client = boto3.client("s3")

DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]
FILE_SUFFIX = os.environ["FILE_SUFFIX"]


def add_drives_to_batch(
    table: str,
    batch_id: str,
    drives_to_process: typing.Dict[str, dict],
    file_suffix: str,
    s3_client: "S3Client",
) -> int:
    """
    Lists files with file_suffix for each prefix in drives_to_process and adds each file to DynamoDB for tracking

    @param table: dynamo tracking table
    @param batch_id: state machine execution id
    @param drives_to_process: {
        "drive1": {"bucket": "addf-example-dev-raw-bucket-xyz", "prefix": "rosbag-scene-detection/drive1/"},
        "drive2": {"bucket": "addf-example-dev-raw-bucket-xyz", "prefix": "rosbag-scene-detection/drive2/"},
    }
    @param file_suffix: ".bag"
    @param s3_client: type boto3.client('s3')
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


def get_drive_files(src_bucket: str, src_prefix: str, file_suffix: str, s3_client: "S3Client") -> typing.List[str]:
    """For a given bucket, prefix, and suffix, lists all files found on S3 and returns a list of the files

    @param drive_id:
    @param src_bucket:
    @param src_prefix:
    @param file_suffix:
    @param s3_client:
    @return:
    """
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


def batch_write_files_to_dynamo(
    table: "DynamoDBServiceResource", drives_and_files: typing.Dict[str, typing.List[str]], batch_id: str
) -> None:
    with table.batch_writer() as writer:
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
                writer.put_item(Item=item)
                idx += 1


def lambda_handler(event: typing.Dict[str, typing.Any], context: typing.Any) -> int:
    drives_to_process = event["DrivesToProcess"]
    execution_id = event["ExecutionID"]

    table = dynamodb_resource.Table(DYNAMODB_TABLE)

    files_in_batch = table.query(
        KeyConditionExpression=Key("pk").eq(execution_id),
        Select="COUNT",
    )["Count"]

    if files_in_batch > 0:
        logger.info("Batch Id already exists in tracking table - using existing batch")
        return {"BatchSize": files_in_batch, "ExecutionID": execution_id}

    logger.info("New Batch Id - collecting unprocessed drives from S3 and adding to the batch")
    files_in_batch = add_drives_to_batch(
        table=table,
        drives_to_process=drives_to_process,
        batch_id=execution_id,
        file_suffix=FILE_SUFFIX,
        s3_client=s3_client,
    )

    if files_in_batch > 10_000:
        raise RuntimeError("Batch Size cannot exceed 10,000")

    return {"BatchSize": files_in_batch, "ExecutionID": execution_id}
