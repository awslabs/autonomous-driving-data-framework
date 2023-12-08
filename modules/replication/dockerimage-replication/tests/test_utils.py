# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import unittest

from helmparser.logging import boto3_logger, logger
from helmparser.utils.utils import deep_merge


class TestMain(unittest.TestCase):
    def test_deep_merge(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 3, "c": 4}
        d3 = {"c": 5, "d": 6}

        result = deep_merge(d1, d2, d3)
        self.assertEqual(result, {"a": 1, "b": 3, "c": 5, "d": 6})

    def test_logger_main(self):
        with self.assertLogs("main", level="INFO") as cm:
            logger.info("first message")
            self.assertEqual(cm.output, ["INFO:main:first message"])

    def test_logger_boto3(self):
        with self.assertLogs("boto3", level="INFO") as cm:
            boto3_logger.info("first message")
            self.assertEqual(cm.output, ["INFO:boto3:first message"])
