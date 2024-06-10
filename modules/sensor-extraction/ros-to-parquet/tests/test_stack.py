# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Template


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
    os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    if "stack" in sys.modules:
        del sys.modules["stack"]


def test_synthesize_stack(stack_defaults):
    import stack

    app = cdk.App()
    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"

    ros_to_parquet = stack.RosToParquetBatchJob(
        scope=app,
        id=f"{project_name}-{dep_name}-{mod_name}",
        project_name=project_name,
        deployment_name=dep_name,
        module_name=mod_name,
        platform="FARGATE",
        ecr_repository_arn="arn:aws:ecr:us-east-1:123456789012:repository/addf-docker-repository",
        s3_access_policy="'arn:aws:iam::123456789012:policy/addf-buckets-us-west-2-123-full-access",
        retries=1,
        timeout_seconds=1800,
        vcpus=2,
        memory_limit_mib=8192,
        stack_description="Testing",
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )

    template = Template.from_stack(ros_to_parquet)
    template.resource_count_is("AWS::Lambda::Function", 2)
    template.resource_count_is("AWS::Batch::JobDefinition", 1)
    template.resource_count_is("AWS::IAM::Role", 3)
    # Check ecr.Repository 'auto_delete' runtime version
    template.has_resource_properties(
        type="AWS::Lambda::Function",
        props={
            "Runtime": "nodejs18.x",
        },
    )
    # Job Definition props
    template.has_resource_properties(
        type="AWS::Batch::JobDefinition",
        props={
            "ContainerProperties": {
                "Command": ["bash", "entrypoint.sh"],
                "ReadonlyRootFilesystem": False,
                "ResourceRequirements": [
                    {"Type": "MEMORY", "Value": "8192"},
                    {"Type": "VCPU", "Value": "2"},
                ],
            },
            "PlatformCapabilities": ["FARGATE"],
            "RetryStrategy": {"Attempts": 1},
            "Timeout": {"AttemptDurationSeconds": 1800},
        },
    )
