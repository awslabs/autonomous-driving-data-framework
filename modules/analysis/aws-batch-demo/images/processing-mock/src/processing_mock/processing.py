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

import argparse
import sys

import boto3
from processing_mock import get_logger

LOGGER = get_logger()


def main(table_name, index, batch_id, s3bucketout) -> int:
    LOGGER.info("s3bucketout: %s", s3bucketout)
    LOGGER.info("batch_id: %s", batch_id)
    LOGGER.info("index: %s", index)
    LOGGER.info("table_name: %s", table_name)

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    item = table.get_item(
        Key={"pk": batch_id, "sk": index},
    ).get("Item", {})

    if not item:
        raise Exception(
            f"pk: {batch_id} sk: {index} not existing in table: {table_name}"
        )

    # DO SOME PROCESSING HERE
    s3 = boto3.client("s3")
    s3.download_file(item["s3_bucket"], item["s3_key"], "/tmp/input.bag")

    output_key = item["s3_key"].replace(".bag", ".json")

    table.update_item(
        Key={"pk": item["drive_id"], "sk": item["file_id"]},
        UpdateExpression="SET "
        "job_status = :status, "
        "output_key = :output_key, "
        "output_bucket = :output_bucket,"
        "s3_key = :s3_key, "
        "s3_bucket = :s3_bucket,"
        "batch_id = :batch_id,"
        "array_index = :index,"
        "drive_id = :drive_id,"
        "file_id = :file_id",
        ExpressionAttributeValues={
            ":status": "success",
            ":output_key": output_key,
            ":output_bucket": s3bucketout,
            ":batch_id": batch_id,
            ":index": index,
            ":s3_key": item["s3_key"],
            ":s3_bucket": item["s3_bucket"],
            ":drive_id": item["drive_id"],
            ":file_id": item["file_id"],
        },
    )
    table.update_item(
        Key={"pk": batch_id, "sk": index},
        UpdateExpression="SET "
        "job_status = :status, "
        "output_key = :output_key, "
        "output_bucket = :output_bucket,"
        "s3_key = :s3_key, "
        "s3_bucket = :s3_bucket,"
        "batch_id = :batch_id,"
        "array_index = :index",
        ExpressionAttributeValues={
            ":status": "success",
            ":output_key": output_key,
            ":output_bucket": s3bucketout,
            ":batch_id": batch_id,
            ":index": index,
            ":s3_key": item["s3_key"],
            ":s3_bucket": item["s3_bucket"],
        },
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Files")
    parser.add_argument("--s3bucketout", required=True)
    parser.add_argument("--batchid", required=True)
    parser.add_argument("--index", required=True)
    parser.add_argument("--tablename", required=True)

    args = parser.parse_args()

    LOGGER.debug("ARGS: %s", args)
    sys.exit(
        main(
            s3bucketout=args.s3bucketout,
            batch_id=args.batchid,
            index=args.index,
            table_name=args.tablename,
        )
    )
