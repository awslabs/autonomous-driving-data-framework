# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Template
from moto import mock_ec2, mock_eks


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    # Unload the app import so that subsequent tests don't reuse

    if "stack" in sys.modules:
        del sys.modules["stack"]


@mock_eks
@mock_ec2
def test_synthesize_stack(stack_defaults):
    import stack

    app = cdk.App()
    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    eks_compute_config = {
        "eks_nodegroup_config": [
            {
                "eks_ng_name": "ng1",
                "eks_node_quantity": 2,
                "eks_node_max_quantity": 5,
                "eks_node_min_quantity": 1,
                "eks_node_disk_size": 20,
                "eks_node_instance_type": "m5.large",
            }
        ],
        "eks_node_spot": "False",
        "eks_api_endpoint_private": "False",
        "eks_secrets_envelope_encryption": "True",
    }

    eks_addons_config = {
        "deploy_aws_lb_controller": "True",
        "deploy_external_dns": "True",
        "deploy_aws_ebs_csi": "True",
        "deploy_aws_efs_csi": "True",
        "deploy_cluster_autoscaler": "True",
        "deploy_metrics_server": "True",
        "deploy_secretsmanager_csi": "True",
        "deploy_external_secrets": "False",
        "deploy_cloudwatch_container_insights_metrics": "True",
        "deploy_cloudwatch_container_insights_logs": "True",
        "cloudwatch_container_insights_logs_retention_days": 7,
        "deploy_amp": "True",
        "deploy_adot": "True",
        "deploy_grafana_for_amp": "True",
        "deploy_kured": "True",
        "deploy_calico": "False",
        "deploy_nginx_controller": {
            "value": "False",
            "nginx_additional_annotations": {
                "nginx.ingress.kubernetes.io/whitelist-source-range": "100.64.0.0/10,10.0.0.0/8"
            },
        },
        "deploy_kyverno": {
            "value": "False",
            "kyverno_policies": {"validate": ["block-ephemeral-containers"]},
        },
    }

    eks_stack = stack.Eks(
        scope=app,
        id=f"{project_name}-{dep_name}-{mod_name}",
        project_name=project_name,
        deployment_name=dep_name,
        module_name=mod_name,
        vpc_id="vpc-12345",
        controlplane_subnet_ids=["subnet-12345", "subnet-54321"],
        dataplane_subnet_ids=["subnet-12345", "subnet-54321"],
        eks_version="1.25",
        eks_compute_config=eks_compute_config,
        eks_addons_config=eks_addons_config,
        custom_subnet_ids=["subnet-12345", "subnet-54321"],
        codebuild_sg_id="sg-12345",
        replicated_ecr_images_metadata={"image": "1234567890.dkr.ecr.image"},
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )

    template = Template.from_stack(eks_stack)

    # EKS Cluster Admin profile
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

    # EKS Cluster role
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "eks.amazonaws.com",
                        },
                    },
                ],
            },
        },
    )

    # template.has_resource_properties("Custom::AWSCDK-EKS-Cluster")
