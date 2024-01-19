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


def test_app(stack_defaults):
    import stack

    app = cdk.App()
    dep_name = "test-deployment"
    mod_name = "test-project"

    stack = stack.DcvImagePublishingStack(
        scope=app,
        id="addf-dcv-image-test-module",
        project_name=mod_name,
        repository_name="test-repo",
        deployment_name=dep_name,
        module_name=mod_name,
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )
    template = Template.from_stack(stack)
    template.resource_count_is("Custom::CDKBucketDeployment", 1)
