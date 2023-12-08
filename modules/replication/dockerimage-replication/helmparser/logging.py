# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Logging module"""
import logging

stream_handler = logging.StreamHandler()
formatter = logging.Formatter("%(message)s")
stream_handler.setFormatter(formatter)

logger = logging.getLogger("main")
logger.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)

boto3_logger = logging.getLogger("boto3")
boto3_logger.setLevel(logging.WARN)
boto3_logger.addHandler(stream_handler)
