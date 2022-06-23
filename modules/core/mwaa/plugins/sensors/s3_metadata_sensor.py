# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import fnmatch
import re
from typing import List
from urllib.parse import urlparse

from airflow.exceptions import AirflowException
from airflow.sensors.base_sensor_operator import BaseSensorOperator
from airflow.utils.decorators import apply_defaults


class S3MetadataSensor(BaseSensorOperator):
    template_fields = ("bucket_key", "bucket_name")

    @apply_defaults
    def __init__(
        self,
        bucket_key,
        bucket_name=None,
        metadata_key: str = "",
        metadata_values: List[str] = "",
        wildcard_match=False,
        aws_conn_id="aws_default",
        verify=None,
        *args,
        **kwargs,
    ):
        super(S3MetadataSensor, self).__init__(*args, **kwargs)
        # Parse
        if bucket_name is None:
            parsed_url = urlparse(bucket_key)
            if parsed_url.netloc == "":
                raise AirflowException("Please provide a bucket_name")
            else:
                bucket_name = parsed_url.netloc
                if parsed_url.path[0] == "/":
                    bucket_key = parsed_url.path[1:]
                else:
                    bucket_key = parsed_url.path
        self.bucket_name = bucket_name
        self.bucket_key = bucket_key
        self.wildcard_match = wildcard_match
        self.aws_conn_id = aws_conn_id
        self.verify = verify
        self.metadata_key = metadata_key
        self.metadata_values = metadata_values

    def poke(self, context):
        self.log.info("Poking for key : s3://%s/%s", self.bucket_name, self.bucket_key)
        return (
            self.get_wildcard_metadata_key(
                wildcard_key=self.bucket_key,
                bucket_name=self.bucket_name,
                metadata_key=self.metadata_key,
                metadata_values=self.metadata_values,
                context=context,
            )
            is not None
        )

    def get_wildcard_metadata_key(self, wildcard_key, bucket_name, metadata_key, metadata_values, context):
        from airflow.hooks.S3_hook import S3Hook

        hook = S3Hook(aws_conn_id=self.aws_conn_id, verify=self.verify)

        if not bucket_name:
            (bucket_name, wildcard_key) = hook.parse_s3_url(wildcard_key)

        prefix = re.split(r"[*]", wildcard_key, 1)[0]
        klist = hook.list_keys(bucket_name, prefix=prefix)
        if klist:
            key_matches = [
                k
                for k in klist
                if fnmatch.fnmatch(k, wildcard_key)
                and not self.has_key_tags(k, bucket_name, metadata_key, metadata_values)
            ]
            if key_matches:
                key = key_matches[0]
                print(f"Pushing key {key} to key 'filename_s3_key'.")
                context["ti"].xcom_push(key="filename_s3_bucket", value=bucket_name)
                context["ti"].xcom_push(key="filename_s3_key", value=key)
                return hook.get_key(key, bucket_name)

    def has_key_tags(self, key, bucket, tag_key, tag_values):
        import boto3

        s3_client = boto3.client("s3")

        response = s3_client.get_object_tagging(Bucket=bucket, Key=key)
        tags = response["TagSet"]

        filtered_tags = list(filter(lambda x: x["Key"] == tag_key, tags))
        if not filtered_tags:
            return False

        return filtered_tags[0]["Value"] in tag_values
