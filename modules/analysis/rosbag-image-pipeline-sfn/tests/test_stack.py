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
    rosbag_stack = stack.TemplateStack(
        scope=app,
        id=f"{project_name}-{dep_name}-{mod_name}",
        project_name=project_name,
        deployment_name=dep_name,
        module_name=mod_name,
        hash="foobar",
        vpc_id="vpc-id",
        source_bucket_name="raw-bucket",
        target_bucket_name="intermediate-bucket",
        logs_bucket_name="logs-bucket",
        artifacts_bucket_name="artifacts-bucket",
        private_subnet_ids='["foo","bar"]',
        emr_job_exec_role_arn="dummy-emr-role",
        emr_app_id="012345678",
        detection_ddb_name="scene-metadata-table",
        on_demand_job_queue_arn="arn:aws:batch:us-west-2:123456789101:job-queue/addf-example",
        fargate_job_queue_arn="arn:aws:batch:us-west-2:123456789101:job-queue/addf-example",
        parquet_batch_job_def_arn="dummyarn",
        png_batch_job_def_arn="dummyarn",
        object_detection_image_uri="dummyuri",
        object_detection_role_arn="dummyrole",
        object_detection_job_concurrency=10,
        object_detection_instance_type="ml.2xlarge",
        lane_detection_image_uri="dummyuri",
        lane_detection_role_arn="dummyrole",
        lane_detection_job_concurrency=10,
        lane_detection_instance_type="ml.2xlarge",
        file_suffix=".bag",
        desired_encoding="bgr8",
        yolo_model="yolov5s",
        stack_description="Testing",
        image_topics='["foo", "bar"]',
        sensor_topics='["foo", "bar"]',
        env=cdk.Environment(
            account=(os.environ["CDK_DEFAULT_ACCOUNT"]),
            region=(os.environ["CDK_DEFAULT_REGION"]),
        ),
    )
    template = Template.from_stack(rosbag_stack)
    template.resource_count_is("AWS::DynamoDB::Table", 1)
    template.resource_count_is("AWS::IAM::Role", 3)
    template.resource_count_is("AWS::StepFunctions::StateMachine", 1)
