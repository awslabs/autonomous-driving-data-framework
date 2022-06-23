# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from airflow.plugins_manager import AirflowPlugin

from sensors.s3_metadata_sensor import *


class S3MetadataPlugin(AirflowPlugin):
    name = "s3_metadata_plugin"

    operators = []
    hooks = []
    sensors = [S3MetadataSensor]
