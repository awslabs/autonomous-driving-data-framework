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
import json
import logging
import os
import sys

import boto3
import fastparquet
import pandas as pd
from bagpy import bagreader

DEBUG_LOGGING_FORMAT = "[%(asctime)s][%(filename)-13s:%(lineno)3d][%(levelname)s][%(threadName)s] %(message)s"
debug = os.environ.get("DEBUG", "False").lower() in [
    "true",
    "yes",
    "1",
]
level = logging.DEBUG if debug else logging.INFO
logging.basicConfig(level=level, format=DEBUG_LOGGING_FORMAT)
logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(level)
if debug:
    logging.getLogger("boto3").setLevel(logging.ERROR)
    logging.getLogger("botocore").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("s3transfer").setLevel(logging.CRITICAL)


class ParquetFromBag:
    def __init__(self, bag_path, topic, output_path, drive_id, file_id):
        clean_topic = topic.replace("/", "_")
        output_dir = os.path.join(output_path, clean_topic)
        os.makedirs(output_dir, exist_ok=True)

        local_parquet_name = os.path.join(output_dir, "data.parquet")

        bag = bagreader(bag_path)
        data = bag.message_by_topic(topic)
        logger.info("Write parquet to {}".format(local_parquet_name))

        self.file = {
            "local_parquet_path": local_parquet_name,
            "topic": clean_topic,
        }

        if data is None:
            logging.info("No data found for {topic}".format(topic=topic))
        else:
            logging.info("Reading data found for {topic}".format(topic=topic))
            df_out = pd.read_csv(data)
            df_out.columns = [x.replace(".", "_") for x in df_out.columns]

            df_out["drive_id"] = drive_id
            df_out["file_id"] = file_id

            fastparquet.write(local_parquet_name, df_out)


def upload(client, bucket_name, drive_id, file_id, files):
    target_prefixes = set()
    for file in files:
        clean_topic = file["topic"]
        target_prefix = os.path.join(drive_id, file_id.replace(".bag", ""), clean_topic)
        target = os.path.join(target_prefix, "data.parquet")
        client.upload_file(file["local_parquet_path"], bucket_name, target)
        target_prefixes.add(target_prefix)
    return list(target_prefixes)


def main(table_name, index, batch_id, topics, target_bucket) -> int:
    logger.info("batch_id: %s", batch_id)
    logger.info("index: %s", index)
    logger.info("table_name: %s", table_name)
    logger.info("topics: %s", topics)
    logger.info("target_bucket: %s", target_bucket)

    # Getting Item to Process
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)
    item = table.get_item(
        Key={"pk": batch_id, "sk": index},
    ).get("Item", {})

    logger.info("Item Pulled: %s", item)

    if not item:
        raise Exception(f"pk: {batch_id} sk: {index} not existing in table: {table_name}")

    drive_id = item["drive_id"]
    file_id = item["file_id"]
    s3 = boto3.client("s3")

    bag_path = "/tmp/ros.bag"
    local_output_path = "/tmp/output"

    logger.info("Downloading Bag")
    s3.download_file(item["s3_bucket"], item["s3_key"], bag_path)
    logger.info(f"Bag downloaded to {bag_path}")

    # save_metadata_to_dynamo(bag, s3_prefix, local_file_name, s3_bucket)

    all_files = []
    for topic in topics:
        logger.info(f"Getting data from topic: {topic}")
        bag_obj = ParquetFromBag(
            topic=topic, bag_path=bag_path, output_path=local_output_path, drive_id=drive_id, file_id=file_id
        )
        all_files.append(bag_obj.file)

    # Sync results
    logger.info(f"Uploading results - {target_bucket}")
    uploaded_directories = upload(s3, target_bucket, drive_id, file_id, all_files)
    logger.info("Uploaded results")

    logger.info("Writing job status to DynamoDB")
    table.update_item(
        Key={"pk": item["drive_id"], "sk": item["file_id"]},
        UpdateExpression="SET "
        "parquet_extraction_status = :parquet_status, "
        "raw_parquet_dirs = :raw_parquet_dirs, "
        "raw_parquet_bucket = :raw_parquet_bucket",
        ExpressionAttributeValues={
            ":parquet_status": "success",
            ":raw_parquet_dirs": uploaded_directories,
            ":raw_parquet_bucket": target_bucket,
        },
    )
    table.update_item(
        Key={"pk": batch_id, "sk": index},
        UpdateExpression="SET "
        "parquet_extraction_status = :parquet_status, "
        "raw_parquet_dirs = :raw_parquet_dirs, "
        "raw_parquet_bucket = :raw_parquet_bucket",
        ExpressionAttributeValues={
            ":parquet_status": "success",
            ":raw_parquet_dirs": uploaded_directories,
            ":raw_parquet_bucket": target_bucket,
        },
    )
    return 0


if __name__ == "__main__":

    # Arguments passed from DAG Code
    parser = argparse.ArgumentParser(description="Process Files")
    parser.add_argument("--tablename", required=True)
    parser.add_argument("--index", required=True)
    parser.add_argument("--batchid", required=True)
    parser.add_argument("--sensortopics", required=True)
    parser.add_argument("--targetbucket", required=True)
    args = parser.parse_args()

    logger.debug("ARGS: %s", args)
    sys.exit(
        main(
            batch_id=args.batchid,
            index=args.index,
            table_name=args.tablename,
            topics=json.loads(args.sensortopics),
            target_bucket=args.targetbucket,
        )
    )
