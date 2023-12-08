# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import unittest

from helmparser.arguments import parse_args


class TestArguments(unittest.TestCase):
    def test_arguments(self):
        parser = parse_args(["-e", "1.25", "-d", "tests_versions", "-p", "000000"])
        self.assertEqual(parser.eks_version, "1.25")
        self.assertEqual(parser.versions_dir, "tests_versions")
        self.assertEqual(parser.registry_prefix, "000000")
        self.assertFalse(parser.update_helm)

    def test_help(self):
        with self.assertRaises(SystemExit) as cm:
            parse_args(["-h"])

        self.assertEqual(cm.exception.code, 0)

    def test_empty_args(self):
        with self.assertRaises(SystemExit) as cm:
            parse_args([])

        self.assertEqual(cm.exception.code, 2)
