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
    os.environ["ADDF_PARAMETER_ON_DEMAND_JOB_QUEUE_ARN"] = "arn:aws:batch:XXX:111111111111:job-queue/demo-XXXX"
    os.environ["ADDF_PARAMETER_MEMORY_LIMIT_MIB"] = "16384"
    os.environ["ADDF_PARAMETER_PLATFORM"] = "EC2"
    os.environ["ADDF_PARAMETER_RETRIES"] = "1"
    os.environ["ADDF_PARAMETER_TIMEOUT_SECONDS"] = "1800"
    os.environ["ADDF_PARAMETER_VCPUS"] = "2"
    os.environ["ADDF_PARAMETER_ARTIFACTS_BUCKET_NAME"] = "artifacts-bucket"
    os.environ["ADDF_PARAMETER_REPOSITORY_NAME"] = "test-repo"

    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401


def test_job_queue_arn(stack_defaults):
    del os.environ["ADDF_PARAMETER_ON_DEMAND_JOB_QUEUE_ARN"]
    with pytest.raises(Exception):
        import app  # noqa: F401

        assert (
            os.environ["ADDF_PARAMETER_ON_DEMAND_JOB_QUEUE_ARN"] == "arn:aws:batch:XXX:111111111111:job-queue/demo-XXXX"
        )


def test_art_buckets_name(stack_defaults):
    del os.environ["ADDF_PARAMETER_ARTIFACTS_BUCKET_NAME"]
    with pytest.raises(Exception):
        import app  # noqa: F401

        assert os.environ["ADDF_PARAMETER_ARTIFACTS_BUCKET_NAME"] == "artifacts-bucket"
