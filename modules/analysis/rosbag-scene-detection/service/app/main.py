import logging
import os
import shutil
import time
from typing import List

import boto3
import fastparquet
import pandas as pd
import yaml
from bagpy import bagreader
from botocore.exceptions import ClientError

logging.getLogger().setLevel(logging.INFO)


def parse_file(
    s3_src_bucket: str,
    s3_src_prefix: str,
    s3_dest_bucket: str,
    s3_dest_bucket_prefix: str,
    topics_to_extract: List[str],
):

    now = str(int(time.time()))

    working_dir = f"/mnt/efs/t{now}"
    input_dir = os.path.join(working_dir, "input")
    output_dir = os.path.join(working_dir, "output")

    clean_directory(working_dir)
    clean_directory(input_dir)
    clean_directory(output_dir)

    # Download File from S3
    local_file = get_object(s3_src_bucket, s3_src_prefix, input_dir)

    # Process File locally
    process_file(local_file, s3_src_prefix, s3_src_bucket, output_dir, topics_to_extract)

    s3_dest_prefix = "bag_parquets"

    # Upload resulting files to S3
    s3_sync_results(s3_dest_bucket, s3_dest_bucket_prefix, s3_dest_prefix, output_dir)

    # Clean up EFS
    shutil.rmtree(working_dir, ignore_errors=True)
    return "Success"


def parse_yaml_val(str_val, obj_start):
    str_val = str_val.replace(f", {obj_start}:", f", NEWOBJ {obj_start}:")
    if str_val[0] == "[":
        str_val = str_val[1:]
    if str_val[-1] == "]":
        str_val = str_val[:-1]
    objects = [yaml.safe_load(x) for x in str_val.split(", NEWOBJ ")]
    return objects


def save_metadata_to_dynamo(bag, s3_prefix, local_file_name, s3_bucket):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ["dynamo_table_name"])
    df = bag.topic_table.to_dict("records")
    logging.info(df)
    item = {
        "bag_file_prefix": s3_prefix,
        "bag_file": local_file_name,
        "bag_file_bucket": s3_bucket,
    }
    for t in df:
        item[t["Topics"]] = {str(k): str(v) for k, v in t.items() if k != "Topics"}

    table.put_item(Item=item)


def process_file(local_file, s3_prefix, s3_bucket, output_dir, topics_to_extract):
    """
    Extract Rosbag Topics from input file to output_dir

    :param local_file:
    :param output_dir:
    :param topics_to_extract:
    :return:
    """

    bag = bagreader(local_file)

    local_file_name = local_file.split("/")[-1].replace(".bag", "")
    save_metadata_to_dynamo(bag, s3_prefix, local_file_name, s3_bucket)

    for topic in topics_to_extract:
        data = bag.message_by_topic(topic)
        if data is None:
            logging.info("No data found for {topic}".format(topic=topic))
        else:
            logging.info("Reading data found for {topic}".format(topic=topic))
            df_out = pd.read_csv(data)
            df_out.columns = [x.replace(".", "_") for x in df_out.columns]
            for col in df_out.columns:
                # parse complex objects:
                example = None
                for x in df_out[col]:
                    if isinstance(x, str) and ":" in x:
                        # Column is yaml
                        example = x
                        break
                if example:
                    obj_start = example.split(":")[0].replace("[", "")
                    df_out[f"{col}_clean"] = df_out[col].apply(lambda x: parse_yaml_val(x, obj_start))

            df_out["bag_file_prefix"] = s3_prefix
            df_out["bag_file_bucket"] = s3_bucket
            clean_topic = topic.replace("/", "_")[1:]
            topic_output_dir = os.path.join(output_dir, clean_topic)
            clean_directory(topic_output_dir)
            topic_output_dir = os.path.join(topic_output_dir, "bag_file=" + local_file_name)
            clean_directory(topic_output_dir)
            output_path = os.path.join(topic_output_dir, "data.parq")
            fastparquet.write(output_path, df_out)
    print_files_in_path(output_dir)


def clean_directory(dir):
    """
    Delete directory if exists, then create the directory
    :param dir:
    :return:
    """
    shutil.rmtree(dir, ignore_errors=True)
    os.mkdir(dir)


def get_object(bucket, object_path, local_dir):
    bag_name = object_path.split("/")[-1]
    local_path = os.path.join(local_dir, bag_name)
    s3 = boto3.client("s3")
    logging.warning("Getting s3://{bucket}/{prefix}".format(bucket=bucket, prefix=object_path))
    s3.download_file(bucket, object_path, local_path)
    return local_path


def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client("s3")
    try:
        s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


def absolute_file_paths(directory):
    for dirpath, _, filenames in os.walk(directory):
        for f in filenames:
            yield os.path.abspath(os.path.join(dirpath, f))


def s3_sync_results(bucket, s3_dest_bucket_prefix, prefix, local_dir):
    """
    Method to easily sync multiple files in a local directory local_dir, to s3://bucket/prefix directory
    :param bucket:
    :param prefix:
    :param s3_dest_bucket_prefix:
    :param local_dir:
    :return:
    """
    files = absolute_file_paths(local_dir)
    for local_path in files:
        logging.info(f"local_path is {local_path}")
        f = local_path.split(local_dir)[-1]
        s3_path = os.path.join(s3_dest_bucket_prefix, prefix, f)
        logging.warning("Uploading " + local_path + " to " + s3_path)
        success = upload_file(local_path, bucket, object_name=s3_path[1:])
        if not success:
            raise ClientError("Failed to upload to s3")


def print_files_in_path(d):
    logging.warning(d)
    fs = absolute_file_paths(d)
    for f in fs:
        logging.warning(f)


if __name__ == "__main__":

    parse_file(
        s3_src_bucket=os.environ["s3_source"],
        s3_src_prefix=os.environ["s3_source_prefix"],
        s3_dest_bucket=os.environ["s3_destination"],
        s3_dest_bucket_prefix=os.environ["s3_dest_bucket_prefix"],
        topics_to_extract=os.environ["topics_to_extract"].split(","),
    )
