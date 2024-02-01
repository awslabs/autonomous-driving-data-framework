# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import pytest


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
    os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
    os.environ["SEEDFARMER_PARAMETER_VPC_ID"] = "vpc-12345"
    os.environ[
        "SEEDFARMER_PARAMETER_OPENSEARCH_DOMAIN_ENDPOINT"
    ] = "vpc-addf-aws-solutions--367e660c-something.us-west-2.es.amazonaws.com"
    os.environ["SEEDFARMER_PARAMETER_OPENSEARCH_SG_ID"] = "sg-084c0dd9dc65c6937"

    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401


def test_missing_vpc_id(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_VPC_ID"]
    with pytest.raises(ValueError):
        import app  # noqa: F401


def test_missing_domain_endpoint(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_OPENSEARCH_DOMAIN_ENDPOINT"]
    with pytest.raises(ValueError):
        import app  # noqa: F401


def test_missing_domain_sg(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_OPENSEARCH_SG_ID"]
    with pytest.raises(ValueError):
        import app  # noqa: F401


def test_solution_description(stack_defaults):
    os.environ["SEEDFARMER_PARAMETER_SOLUTION_ID"] = "SO123456"
    os.environ["SEEDFARMER_PARAMETER_SOLUTION_NAME"] = "MY GREAT TEST"
    os.environ["SEEDFARMER_PARAMETER_SOLUTION_VERSION"] = "v1.0.0"

    import app

    ver = app.generate_description()
    assert ver == "(SO123456) MY GREAT TEST. Version v1.0.0"


def test_solution_description_no_version(stack_defaults):
    os.environ["SEEDFARMER_PARAMETER_SOLUTION_ID"] = "SO123456"
    os.environ["SEEDFARMER_PARAMETER_SOLUTION_NAME"] = "MY GREAT TEST"
    del os.environ["SEEDFARMER_PARAMETER_SOLUTION_VERSION"]

    import app

    ver = app.generate_description()
    assert ver == "(SO123456) MY GREAT TEST"
