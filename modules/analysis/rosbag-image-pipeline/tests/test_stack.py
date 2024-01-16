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


def iam_policy() -> dict:
    return {
        "Policies": [
            {
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": "dynamodb:*",
                            "Effect": "Allow",
                            "Resource": "arn:aws:dynamodb:us-east-1:111111111111:table/addf-test-deployment-test-module*",
                        },
                        {
                            "Action": "ecr:*",
                            "Effect": "Allow",
                            "Resource": "arn:aws:ecr:us-east-1:111111111111:repository/addf-test-deployment-test-module*",
                        },
                        {
                            "Action": [
                                "batch:UntagResource",
                                "batch:DeregisterJobDefinition",
                                "batch:TerminateJob",
                                "batch:CancelJob",
                                "batch:SubmitJob",
                                "batch:RegisterJobDefinition",
                                "batch:TagResource",
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "job-queue-1",
                                "job-queue-2",
                                "job-def-1",
                                "job-def-2",
                                "arn:aws:batch:us-east-1:111111111111:job/*",
                            ],
                        },
                        {
                            "Action": "iam:PassRole",
                            "Effect": "Allow",
                            "Resource": [
                                "obj-detection-role",
                                "lane-detection-role",
                            ],
                        },
                        {
                            "Action": ["batch:Describe*", "batch:List*"],
                            "Effect": "Allow",
                            "Resource": "*",
                        },
                        {
                            "Action": [
                                "s3:GetObject",
                                "s3:GetObjectAcl",
                                "s3:ListBucket",
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "arn:aws:s3:::addf-*",
                                "arn:aws:s3:::addf-*/*",
                            ],
                        },
                    ]
                }
            }
        ],
    }


def test_stack(stack_defaults):
    import stack

    app = cdk.App()
    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"

    rosbag_stack = stack.AwsBatchPipeline(
        scope=app,
        id=f"{project_name}-{dep_name}-{mod_name}",
        deployment_name=dep_name,
        module_name=mod_name,
        vpc_id="vpc-id",
        mwaa_exec_role="mwaa-exec-role",
        bucket_access_policy="bucket-access-policy",
        object_detection_role="obj-detection-role",
        lane_detection_role="lane-detection-role",
        job_queues=["job-queue-1", "job-queue-2"],
        job_definitions=["job-def-1", "job-def-2"],
        stack_description="Testing",
        env=cdk.Environment(
            account=(os.environ["CDK_DEFAULT_ACCOUNT"]),
            region=(os.environ["CDK_DEFAULT_REGION"]),
        ),
    )
    template = Template.from_stack(rosbag_stack)

    template.resource_count_is("AWS::DynamoDB::Table", 1)

    template.resource_count_is("AWS::IAM::Role", 1)
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {"AWS": "mwaa-exec-role"},
                    }
                ],
                "Version": "2012-10-17",
            },
            "ManagedPolicyArns": [
                "bucket-access-policy",
                {
                    "Fn::Join": [
                        "",
                        [
                            "arn:",
                            {"Ref": "AWS::Partition"},
                            ":iam::aws:policy/AmazonSageMakerFullAccess",
                        ],
                    ]
                },
            ],
        },
    )
    template.has_resource_properties("AWS::IAM::Role", iam_policy())
