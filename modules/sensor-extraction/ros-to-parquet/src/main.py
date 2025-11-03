# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import argparse
import json
import logging
import os
import sys
import zipfile

import boto3
import fastparquet
import pandas as pd
import requests
import rclpy
from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message

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
    def __init__(self, ros2_path, topic, output_path, drive_id, file_id):
        clean_topic = topic.replace("/", "_")
        output_dir = os.path.join(output_path, clean_topic)
        os.makedirs(output_dir, exist_ok=True)

        local_parquet_name = os.path.join(output_dir, "data.parquet")

        storage_options = StorageOptions(uri=ros2_path, storage_id='sqlite3')
        converter_options = ConverterOptions('', '')
        reader = SequentialReader()
        reader.open(storage_options, converter_options)
        
        topic_types = reader.get_all_topics_and_types()
        type_map = {topic_types[i].name: topic_types[i].type for i in range(len(topic_types))}
        
        # Collect all messages for this topic
        messages = []
        while reader.has_next():
            (topic_name, data, timestamp) = reader.read_next()
            if topic_name == topic:
                msg_type = get_message(type_map[topic_name])
                msg = deserialize_message(data, msg_type)
                
                # Convert message to dict (this is simplified - you may need custom logic per message type)
                msg_dict = self._message_to_dict(msg)
                msg_dict['timestamp'] = timestamp
                msg_dict['drive_id'] = drive_id
                msg_dict['file_id'] = file_id
                messages.append(msg_dict)
        
        reader.close()

        self.file = {
            "local_parquet_path": local_parquet_name,
            "topic": clean_topic,
        }

        if not messages:
            logging.info("No data found for {topic}".format(topic=topic))
        else:
            logging.info("Reading data found for {topic}".format(topic=topic))
            df_out = pd.DataFrame(messages)
            df_out.columns = [x.replace(".", "_") for x in df_out.columns]
            fastparquet.write(local_parquet_name, df_out)

    def _message_to_dict(self, msg):
        """Convert ROS2 message to dictionary - simplified version"""
        result = {}
        for field_name in msg.get_fields_and_field_types():
            try:
                value = getattr(msg, field_name)
                # Handle basic types - you may need to expand this for complex types
                if hasattr(value, 'get_fields_and_field_types'):
                    result[field_name] = self._message_to_dict(value)
                else:
                    result[field_name] = value
            except:
                result[field_name] = None
        return result


def upload(client, bucket_name, drive_id, file_id, files):
    target_prefixes = set()
    for file in files:
        clean_topic = file["topic"]
        target_prefix = os.path.join(drive_id, file_id.replace(".zip", ""), clean_topic)
        target = os.path.join(target_prefix, "data.parquet")
        client.upload_file(file["local_parquet_path"], bucket_name, target)
        target_prefixes.add(target_prefix)
    return list(target_prefixes)


def get_log_path():
    response = requests.get(f"{os.environ['ECS_CONTAINER_METADATA_URI_V4']}", timeout=10)
    task_region = response.json()["LogOptions"]["awslogs-region"]
    return task_region, response.json()["LogOptions"]["awslogs-stream"].replace("/", "$252F")


def save_job_url_and_logs(table, drive_id, file_id, batch_id, index):
    job_region, log_path = get_log_path()
    job_url = (
        f"https://{job_region}.console.aws.amazon.com/batch/home?region={job_region}#jobs/detail/"
        f"{os.environ['AWS_BATCH_JOB_ID']}"
    )

    job_cloudwatch_logs = (
        f"https://{job_region}.console.aws.amazon.com/cloudwatch/home?region={job_region}#"
        f"logsV2:log-groups/log-group/$252Faws$252Fbatch$252Fjob/log-events/{log_path}"
    )

    table.update_item(
        Key={"pk": drive_id, "sk": file_id},
        UpdateExpression="SET "
        "parquet_extraction_batch_job = :batch_url, "
        "parquet_extraction_job_logs = :cloudwatch_logs",
        ExpressionAttributeValues={
            ":cloudwatch_logs": job_cloudwatch_logs,
            ":batch_url": job_url,
        },
    )

    table.update_item(
        Key={"pk": batch_id, "sk": index},
        UpdateExpression="SET "
        "parquet_extraction_batch_job = :batch_url, "
        "parquet_extraction_job_logs = :cloudwatch_logs",
        ExpressionAttributeValues={
            ":cloudwatch_logs": job_cloudwatch_logs,
            ":batch_url": job_url,
        },
    )


def main(table_name, index, batch_id, zip_path, local_output_path, topics, target_bucket) -> int:
    logger.info("batch_id: %s", batch_id)
    logger.info("index: %s", index)
    logger.info("table_name: %s", table_name)
    logger.info("zip_path: %s", zip_path)
    logger.info("local_output_path: %s", local_output_path)
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
        raise ValueError(f"pk: {batch_id} sk: {index} not existing in table: {table_name}")

    drive_id = item["drive_id"]
    file_id = item["file_id"]
    s3 = boto3.client("s3")

    save_job_url_and_logs(table, drive_id, file_id, batch_id, index)

    logger.info("Downloading zip file")
    s3.download_file(item["s3_bucket"], item["s3_key"], zip_path)
    logger.info(f"Zip downloaded to {zip_path}")

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(os.path.dirname(zip_path))
    logger.info(f"Extracted zip to {os.path.dirname(zip_path)}")

    file_name = item["file_id"].replace(".zip", "")
    ros2_path = f"{os.path.dirname(zip_path)}/{file_name}"
    logger.info(f"ROS2 directory at {ros2_path}")

    all_files = []
    for topic in topics:
        logger.info(f"Getting data from topic: {topic}")
        ros2_obj = ParquetFromBag(
            topic=topic,
            ros2_path=ros2_path,
            output_path=local_output_path,
            drive_id=drive_id,
            file_id=file_id,
        )
        all_files.append(ros2_obj.file)

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
            zip_path="/tmp/ros.zip",
            local_output_path="/tmp/output",
            topics=json.loads(args.sensortopics),
            target_bucket=args.targetbucket,
        )
    )
