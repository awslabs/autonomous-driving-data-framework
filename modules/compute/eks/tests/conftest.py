# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os


def pytest_generate_tests(metafunc):
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["VERSIONS_DIR"] = "tests/versions"
