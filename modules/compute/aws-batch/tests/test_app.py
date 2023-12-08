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
    os.environ["SEEDFARMER_PARAMETER_RETENTION_TYPE"] = "DESTROY"
    os.environ["SEEDFARMER_PARAMETER_VPC_ID"] = "vpc-12345"
    os.environ["SEEDFARMER_PARAMETER_PRIVATE_SUBNET_IDS"] = '["subnet-12345", "subnet-54321"]'
    os.environ[
        "SEEDFARMER_PARAMETER_BATCH_COMPUTE"
    ] = '{"batch_compute_config": [{"env_name": "ng1", "compute_type": "ON_DEMAND", "max_vcpus": 4800, "desired_vcpus": 0, "order": 1, "instance_types": ["m5.xlarge"]}, {"env_name": "ng2", "max_vcpus": 4800, "desired_vcpus": 0, "compute_type": "SPOT", "order": 1}, {"env_name": "ng3", "max_vcpus": 4800, "desired_vcpus": 0, "compute_type": "FARGATE", "order": 1}]}'  # type: ignore
    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401


def test_project_deployment_name_length(stack_defaults):
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project-incredibly"

    with pytest.raises(Exception) as e:
        import app  # noqa: F401
    assert "module cannot support a project+deployment name character length greater than" in str(e)


def test_vpc_id(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_VPC_ID"]

    with pytest.raises(Exception):
        import app  # noqa: F401

        assert os.environ["SEEDFARMER_PARAMETER_VPC_ID"] == "vpc-12345"


def test_private_subnet_ids(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_PRIVATE_SUBNET_IDS"]

    with pytest.raises(Exception):
        import app  # noqa: F401

        assert os.environ["SEEDFARMER_PARAMETER_PRIVATE_SUBNET_IDS"] == ["subnet-12345", "subnet-54321"]


def test_batch_cmpute(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_BATCH_COMPUTE"]

    with pytest.raises(Exception):
        import app  # noqa: F401

        assert os.environ["SEEDFARMER_PARAMETER_BATCH_COMPUTE"] == {
            "batch_compute_config": [
                {
                    "env_name": "ng1",
                    "compute_type": "ON_DEMAND",
                    "max_vcpus": 4800,
                    "desired_vcpus": 0,
                    "order": 1,
                    "instance_types": ["m5.xlarge"],
                },
                {"env_name": "ng2", "max_vcpus": 4800, "desired_vcpus": 0, "compute_type": "SPOT", "order": 1},
                {"env_name": "ng3", "max_vcpus": 4800, "desired_vcpus": 0, "compute_type": "FARGATE", "order": 1},
            ]
        }


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
