# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import pytest


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["ADDF_DEPLOYMENT_NAME"] = "test-proj"
    os.environ["ADDF_MODULE_NAME"] = "test-dep"
    os.environ["ADDF_HASH"] = "hash"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
    os.environ["ADDF_PARAMETER_ENCRYPTION_TYPE"] = "SSE"
    os.environ["ADDF_PARAMETER_RETENTION_TYPE"] = "DESTROY"

    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401


def test_buckets_encryption_type(stack_defaults):
    del os.environ["ADDF_PARAMETER_ENCRYPTION_TYPE"]

    with pytest.raises(Exception):
        import app  # noqa: F401

        assert os.environ["ADDF_PARAMETER_ENCRYPTION_TYPE"] == "SSE"


def test_invalid_buckets_encryption_type(stack_defaults):
    os.environ["ADDF_PARAMETER_ENCRYPTION_TYPE"] = "notvalid"
    with pytest.raises(Exception):
        import app  # noqa: F401


def test_buckets_retention(stack_defaults):
    del os.environ["ADDF_PARAMETER_RETENTION_TYPE"]

    with pytest.raises(Exception):
        import app  # noqa: F401

        assert os.environ["ADDF_PARAMETER_RETENTION_TYPE"] == "DESTROY"


def test_invalid_retention_type(stack_defaults):
    os.environ["ADDF_PARAMETER_RETENTION_TYPE"] = "notvalid"
    with pytest.raises(Exception):
        import app  # noqa: F401


def test_solution_description(stack_defaults):
    os.environ["ADDF_PARAMETER_SOLUTION_ID"] = "SO123456"
    os.environ["ADDF_PARAMETER_SOLUTION_NAME"] = "MY GREAT TEST"
    os.environ["ADDF_PARAMETER_SOLUTION_VERSION"] = "v1.0.0"

    import app

    ver = app.generate_description()
    assert ver == "(SO123456) MY GREAT TEST. Version v1.0.0"


def test_solution_description_no_version(stack_defaults):
    os.environ["ADDF_PARAMETER_SOLUTION_ID"] = "SO123456"
    os.environ["ADDF_PARAMETER_SOLUTION_NAME"] = "MY GREAT TEST"
    del os.environ["ADDF_PARAMETER_SOLUTION_VERSION"]

    import app

    ver = app.generate_description()
    assert ver == "(SO123456) MY GREAT TEST"
