# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Template


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["ADDF_PROJECT_NAME"] = "test-project"
    os.environ["ADDF_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["ADDF_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    if "stack" in sys.modules:
        del sys.modules["stack"]


def test_synthesize_stack(stack_defaults):
    import stack

    app = cdk.App()
    dep_name = "test-deployment"
    mod_name = "test-module"

    image_extraction_stack = stack.ImageExtraction(
        scope=app,
        id=f"addf-{dep_name}-{mod_name}",
        deployment_name=dep_name,
        module_name=mod_name,
        platform="EC2",
        retries=1,
        timeout_seconds=1800,
        vcpus=2,
        memory_limit_mib=8192,
        repository_name="test-repo",
        artifacts_bucket_name="artifacts-bucket",
        on_demand_job_queue_arn="arn:aws:batch:XXX:111111111111:job-queue/demo-XXXX",
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )

    template = Template.from_stack(image_extraction_stack)
    template.resource_count_is("AWS::StepFunctions::StateMachine", 1)
    template.resource_count_is("AWS::Events::Rule", 1)
    template.resource_count_is("AWS::Batch::JobDefinition", 1)

    # Check ecr custom resource runtime version
    template.has_resource_properties(
        type="AWS::Lambda::Function",
        props={
            "Runtime": "provided.al2023",
        },
    )
