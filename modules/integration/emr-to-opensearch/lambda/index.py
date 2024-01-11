# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import datetime
import gzip
import hashlib
import io
import logging
import os
import re
from urllib.parse import unquote_plus

import boto3
from elasticsearch import Elasticsearch, RequestsHttpConnection
from elasticsearch import helpers as es_helpers
from requests_aws4auth import AWS4Auth

# vars
region = os.getenv("REGION", "")
host = os.getenv("DOMAIN_ENDPOINT", "")
index = "emrlogs"
ES_BULK_BATCH_SIZE = 1000

# Client connections
s3 = boto3.client("s3")

# Logging
_logger: logging.Logger = logging.getLogger(__name__)


def get_file_timestamp(bucket_name, object_key):
    response = s3.head_object(
        Bucket=bucket_name,
        Key=object_key,
    )

    return response["LastModified"]


def download_logs(bucket_name, object_key):
    # Download the *.gz file
    gz_file = io.BytesIO()
    s3.download_fileobj(bucket_name, object_key, gz_file)

    # Decompress
    gz_file.seek(0)
    log_file = gzip.GzipFile(fileobj=gz_file)

    # Decode into text
    log_content = log_file.read().decode("UTF-8")

    return log_content.splitlines()


def enrich_log(log_entry):
    # Extract EMR cluster/step ID from the file path
    re_match = re.search("/(j-[\w]+)/steps/(s-[\w]+)/", log_entry["log_file"])
    if re_match:
        log_entry["emr_cluster_id"] = re_match.group(1)
        log_entry["emr_step_id"] = re_match.group(2)
    else:
        re_match = re.search("/(j-[\w]+)/", log_entry["log_file"])
        if re_match:
            log_entry["emr_cluster_id"] = re_match.group(1)


def transform_log(raw_log, line_number, file_timestamp, key, bucket, region):
    log_entry = {
        "raw_log": raw_log,
    }

    log_entry["log_file_line_number"] = line_number
    log_entry["log_file"] = f"s3://{bucket}/{key}"
    log_entry["log_file_timestamp"] = file_timestamp.isoformat()
    log_entry["aws_region"] = region

    enrich_log(log_entry)

    return log_entry


def create_log_id(log_entry):
    raw_id = "{}|{}".format(log_entry["log_file"], log_entry["log_file_line_number"])
    return hashlib.sha256(bytes(raw_id.encode("utf-8"))).hexdigest()


def store_logs(logs, es_client):
    bulk_logs = [
        {
            "_index": f"{index}-{datetime.datetime.utcnow().date().isoformat()}",
            "_type": "emr_log",
            "_id": create_log_id(log),
            "_source": log,
        }
        for log in logs
    ]

    response = es_helpers.bulk(es_client, bulk_logs)
    _logger.info("RESPONSE: %s", response)


def create_es_client():
    service = "es"
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        service,
        session_token=credentials.token,
    )

    return Elasticsearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )


def handler(event, _context):
    es = create_es_client()
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        file_timestamp = get_file_timestamp(bucket, key)
        raw_logs = download_logs(bucket, key)
        total_count = len(raw_logs)

        _logger.info("Number of entries in the log: %s", total_count)

        batch = []
        batch_number = 1
        skipped_entries_count = 0

        for line_number, line in enumerate(raw_logs, start=1):
            if not line.strip():
                skipped_entries_count += 1
            else:
                log_entry = transform_log(
                    line,
                    line_number,
                    file_timestamp,
                    key,
                    bucket,
                    region,
                )
                batch.append(log_entry)

            if len(batch) >= ES_BULK_BATCH_SIZE or line_number == total_count:
                _logger.info(f"Saving batch {batch_number} containing {len(batch)} entries...")
                store_logs(batch, es)
                batch = []
                batch_number += 1

        if skipped_entries_count > 0:
            _logger.debug(f"Skipped {skipped_entries_count} entries")
