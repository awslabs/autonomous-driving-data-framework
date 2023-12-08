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
    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    batch_compute = {
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
    efs_stack = stack.AwsBatch(
        scope=app,
        id=f"{project_name}-{dep_name}-{mod_name}",
        project_name=project_name,
        deployment_name=dep_name,
        module_name=mod_name,
        vpc_id="vpc-12345",
        private_subnet_ids=["subnet-12345", "subnet-54321"],
        batch_compute=batch_compute,
        stack_description="Testing",
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )

    template = Template.from_stack(efs_stack)
    template.resource_count_is("AWS::Batch::ComputeEnvironment", 3)
    template.resource_count_is("AWS::Batch::JobQueue", 3)

    # Batch Instance profile
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "ec2.amazonaws.com",
                        },
                    },
                ],
            },
        },
    )

    # Batch Service role
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "batch.amazonaws.com",
                        },
                    },
                ],
            },
        },
    )
