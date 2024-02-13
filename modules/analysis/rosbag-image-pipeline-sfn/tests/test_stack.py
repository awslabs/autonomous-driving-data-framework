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
        target_bucket_name="intermediate-bucket",
        logs_bucket_name="logs-bucket",
        artifacts_bucket_name="artifacts-bucket",
        bucket_access_policy="bucket-access-policy",
        job_queues={
            "fargate_job_queue": "queue",
            "spot_job_queue": "queue",
            "on_demand_job_queue": "queue",
        },
        job_definitions={
            "png_batch_job_def_arn": "dummyarn",
            "parquet_batch_job_def_arn": "dummyarn",
        },
        lane_detection_config={
            "LaneDetectionImageUri": "dummyuri",
            "LaneDetectionRole": "dummyrole",
            "LaneDetectionJobConcurrency": "10",
            "LaneDetectionInstanceType": "m5.xlarge",
            "LaneDetectionRole": "dummy-sagemaker-role",
        },
        object_detection_config={
            "ObjectDetectionImageUri": "dummyuri",
            "ObjectDetectionRole": "dummyrole",
            "ObjectDetectionJobConcurrency": "10",
            "ObjectDetectionInstanceType": "m5.xlarge",
            "ObjectDetectionRole": "dummy-sagemaker-role",
        },
        emr_job_config={
            "EMRApplicationId": "012345678",
            "EMRJobRole": "dummy-emr-role",
        },
        stack_description="Testing",
        image_topics='["foo", "bar"]',
        rosbag_scene_metadata_table="scene-metadata-table",
        env=cdk.Environment(
            account=(os.environ["CDK_DEFAULT_ACCOUNT"]),
            region=(os.environ["CDK_DEFAULT_REGION"]),
        ),
    )
    template = Template.from_stack(rosbag_stack)

    template.resource_count_is("AWS::DynamoDB::Table", 1)

    template.resource_count_is("AWS::IAM::Role", 1)
