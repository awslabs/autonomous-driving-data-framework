# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import pytest


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["ADDF_PROJECT_NAME"] = "test-project"
    os.environ["ADDF_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["ADDF_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
    os.environ["ADDF_PARAMETER_VPC_ID"] = "vpc-12345"
    os.environ[
        "ADDF_PARAMETER_OPENSEARCH_DOMAIN_ENDPOINT"
    ] = "vpc-addf-aws-solutions--367e660c-something.us-west-2.es.amazonaws.com"
    os.environ["ADDF_PARAMETER_OPENSEARCH_SG_ID"] = "sg-084c0dd9dc65c6937"

    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401


def test_missing_vpc_id(stack_defaults):
    del os.environ["ADDF_PARAMETER_VPC_ID"]
    with pytest.raises(ValueError):
        import app  # noqa: F401


def test_missing_domain_endpoint(stack_defaults):
    del os.environ["ADDF_PARAMETER_OPENSEARCH_DOMAIN_ENDPOINT"]
    with pytest.raises(ValueError):
        import app  # noqa: F401


def test_missing_domain_sg(stack_defaults):
    del os.environ["ADDF_PARAMETER_OPENSEARCH_SG_ID"]
    with pytest.raises(ValueError):
        import app  # noqa: F401
