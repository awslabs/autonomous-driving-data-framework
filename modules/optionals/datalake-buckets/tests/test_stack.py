# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Template


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    # Unload the app import so that subsequent tests don't reuse

    if "stack" in sys.modules:
        del sys.modules["stack"]


def test_synthesize_stack(stack_defaults):
    import stack

    app = cdk.App()
    dep_name = "test-deployment"
    mod_name = "test-module"

    metadata_storage_stack = stack.DataLakeBucketsStack(
        scope=app,
        id=f"addf-{dep_name}-{mod_name}",
        deployment_name=dep_name,
        module_name=mod_name,
        hash="hash",
        buckets_encryption_type="SSE",
        buckets_retention="DESTROY",
        artifacts_log_retention=2,
        stack_description="Testing",
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )

    template = Template.from_stack(metadata_storage_stack)
    template.resource_count_is("AWS::S3::Bucket", 5)
