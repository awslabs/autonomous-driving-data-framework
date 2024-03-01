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

    batch_config = {
        "retries": 1,
        "timeout_seconds": 1800,
        "vcpus": 2,
        "memory_limit_mib": 8192,
        "resized_width": 1280,
        "resized_height": 720,
    }

    ros_to_png = stack.RosToPngBatchJob(
        scope=app,
        id=f"addf-{dep_name}-{mod_name}",
        deployment_name=dep_name,
        module_name=mod_name,
        s3_access_policy="arn:aws:iam::123456789012:policy/addf-buckets-us-west-2-123-full-access",
        batch_config=batch_config,
        stack_description="Testing",
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )

    template = Template.from_stack(ros_to_png)
    template.resource_count_is("AWS::ECR::Repository", 1)
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
    # Check batch job definition properties
    template.has_resource_properties(
        type="AWS::Batch::JobDefinition",
        props={
            "ContainerProperties": {
                "MountPoints": [{"ContainerPath": "/mnt/ebs", "ReadOnly": False, "SourceVolume": "scratch"}],
                "ReadonlyRootFilesystem": False,
                "ResourceRequirements": [{"Type": "MEMORY", "Value": "8192"}, {"Type": "VCPU", "Value": "2"}],
                "Volumes": [{"Name": "scratch"}],
            }
        },
    )


def test_synthesize_stack_without_resize(stack_defaults):
    import stack

    app = cdk.App()
    dep_name = "test-deployment"
    mod_name = "test-module"

    batch_config = {
        "retries": 1,
        "timeout_seconds": 1800,
        "vcpus": 2,
        "memory_limit_mib": 8192,
    }

    ros_to_png = stack.RosToPngBatchJob(
        scope=app,
        id=f"addf-{dep_name}-{mod_name}",
        deployment_name=dep_name,
        module_name=mod_name,
        s3_access_policy="arn:aws:iam::123456789012:policy/addf-buckets-us-west-2-123-full-access",
        batch_config=batch_config,
        stack_description="Testing",
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )

    template = Template.from_stack(ros_to_png)
    template.resource_count_is("AWS::ECR::Repository", 1)
    template.resource_count_is("AWS::Lambda::Function", 2)
    template.resource_count_is("AWS::Batch::JobDefinition", 1)
    template.resource_count_is("AWS::IAM::Role", 3)
