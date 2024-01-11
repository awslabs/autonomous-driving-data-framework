# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import aws_cdk as cdk
import pytest
from aws_cdk import Environment
from aws_cdk.assertions import Template


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["CDK_DEFAULT_ACCOUNT"] = "1234567890"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    # Unload the app import so that subsequent tests don't reuse

    if "stack" in sys.modules:
        del sys.modules["stack"]


def test_app(stack_defaults):
    import stack

    app = cdk.App()
    stack = stack.DcvEksStack(
        scope=app,
        id="test-proj",
        project_name="test_proj",
        deployment_name="test_deploy",
        module_name="test_module",
        dcv_namespace="dcv",
        dcv_image_uri="docker.ecr.test_image_uri:dcv-latest",
        eks_cluster_name="test_cluster",
        eks_cluster_admin_role_arn="arn:aws:iam:us-east-1:1234567890:role/test-role",
        eks_oidc_arn="arn:aws:eks:us-east-1:1234567890:oidc-provider/oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/test-ocid",
        eks_cluster_open_id_connect_issuer="test_open_id_connect_issuer",
        eks_cluster_security_group_id="sg-1234567890",
        eks_node_role_arn="arn:aws:iam:us-east-1:1234567890:role/test-role",
        dcv_node_port=31888,
        env=Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )
    template = Template.from_stack(stack)
    template.resource_count_is("AWS::IAM::Role", 1)
    template.resource_count_is("AWS::IAM::Policy", 2)
    template.resource_count_is("Custom::AWSCDK-EKS-KubernetesResource", 7)
    template.resource_count_is("AWS::EC2::SecurityGroupIngress", 2)
