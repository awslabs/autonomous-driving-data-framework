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
        "ADDF_PARAMETER_PRIVATE_SUBNET_IDS"
    ] = '["subnet-00ffc51481090f2d4", "subnet-061322cd815e741e9", "subnet-089eccb47c3d29bf8"]'
    os.environ["ADDF_PARAMETER_OPENSEARCH_SG_ID"] = "sg-084c0dd9dc65c6937"
    os.environ["ADDF_PARAMETER_OPENSEARCH_DOMAIN_NAME"] = "mydomain"
    os.environ[
        "ADDF_PARAMETER_OPENSEARCH_DOMAIN_ENDPOINT"
    ] = "vpc-addf-aws-solutions--367e660c-k57drotm5ampt5nt7ftfnse4pi.us-west-2.es.amazonaws.com"
    os.environ[
        "ADDF_PARAMETER_ROSBAG_STREAM_ARN"
    ] = "arn:aws:dynamodb:us-west-2:123456789012:table/addf-/stream/2023-08-15T03:16:51.909"
    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults, mocker):
    # mocker.patch("stack.PythonLayerVersion", return_value=None)
    # mocker.patch("stack.PythonFunction", return_value=None)
    # mocker.patch("stack.PythonFunction.add_event_source_mapping", return_value=None)
    mocker.patch("stack.DDBtoOpensearch", return_value=None)
    try:
        import app  # noqa: F401
    except AttributeError:
        pass


def test_missing_vpc_id(stack_defaults):
    del os.environ["ADDF_PARAMETER_VPC_ID"]
    with pytest.raises(ValueError):
        import app  # noqa: F401


def test_missing_subnet_id(stack_defaults):
    del os.environ["ADDF_PARAMETER_PRIVATE_SUBNET_IDS"]
    with pytest.raises(ValueError):
        import app  # noqa: F401


# Omitting as docker build not working in codebuild currently
# def test_solution_description(stack_defaults):
#     os.environ["ADDF_PARAMETER_SOLUTION_ID"] = "SO123456"
#     os.environ["ADDF_PARAMETER_SOLUTION_NAME"] = "MY GREAT TEST"
#     os.environ["ADDF_PARAMETER_SOLUTION_VERSION"] = "v1.0.0"

#     from app import generate_description

#     ver = generate_description()
#     assert ver == "(SO123456) MY GREAT TEST. Version v1.0.0"


# def test_solution_description_no_version(stack_defaults):
#     os.environ["ADDF_PARAMETER_SOLUTION_ID"] = "SO123456"
#     os.environ["ADDF_PARAMETER_SOLUTION_NAME"] = "MY GREAT TEST"
#     del os.environ["ADDF_PARAMETER_SOLUTION_VERSION"]

#     from app import generate_description

#     ver = generate_description()
#     assert ver == "(SO123456) MY GREAT TEST"
