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

    lane_det_stack = stack.LaneDetection(
        scope=app,
        id=f"addf-{dep_name}-{mod_name}",
        deployment_name=dep_name,
        module_name=mod_name,
        s3_access_policy="arn:aws:policy:12345:XXX",
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )

    template = Template.from_stack(lane_det_stack)
    template.resource_count_is("AWS::ECR::Repository", 1)
    template.resource_count_is("AWS::IAM::Role", 2)
