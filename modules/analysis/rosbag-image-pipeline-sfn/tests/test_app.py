# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import pytest


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
    os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
    os.environ[
        "SEEDFARMER_PARAMETER_SENSOR_TOPICS"
    ] = '["/vehicle/gps/fix,/vehicle/gps/time,/vehicle/gps/vel,/imu_raw"]'
    os.environ["SEEDFARMER_PARAMETER_LANE_DETECTION_INSTANCE_TYPE"] = "ml.m5.2xlarge"
    os.environ["SEEDFARMER_PARAMETER_LANE_DETECTION_JOB_CONCURRENCY"] = "20"
    os.environ[
        "SEEDFARMER_PARAMETER_IMAGE_TOPICS"
    ] = '["/flir_adk/rgb_front_left/image_raw", "/flir_adk/rgb_front_right/image_raw"]'
    os.environ[
        "SEEDFARMER_PARAMETER_OBJECT_DETECTION_IMAGE_URI"
    ] = "1234567891011.dkr.ecr.us-west-2.amazonaws.com/addf-sfn-example-docker-images-object-detection:latest"
    os.environ["SEEDFARMER_PARAMETER_INTERMEDIATE_BUCKET"] = "addf-sfn-example-intermediate-bucket-foobar"
    os.environ[
        "SEEDFARMER_PARAMETER_EMR_JOB_EXEC_ROLE"
    ] = "arn:aws:iam::1234567891011:role/addf-sfn-example-core-emr-addfsfnexamplecoreemrserv-nDO07m4q6ZUG"
    os.environ[
        "SEEDFARMER_PARAMETER_ROSBAG_SCENE_METADATA_TABLE"
    ] = "addf-sfn-example-core-metadata-storage-Rosbag-Scene-Metadata"
    os.environ[
        "SEEDFARMER_PARAMETER_LANE_DETECTION_IAM_ROLE"
    ] = "arn:aws:iam::1234567891011:role/addf-sfn-example-docker-i-addfsfnexampledockerimage-Vc0u6FvNyMOu"
    os.environ["SEEDFARMER_PARAMETER_OBJECT_DETECTION_INSTANCE_TYPE"] = "ml.m5.xlarge"
    os.environ[
        "SEEDFARMER_PARAMETER_PNG_BATCH_JOB_DEF_ARN"
    ] = "arn:aws:batch:us-west-2:1234567891011:job-definition/addf-sfn-example-docker-images-ros-to-png:1"
    os.environ[
        "SEEDFARMER_PARAMETER_FARGATE_JOB_QUEUE_ARN"
    ] = "arn:aws:batch:us-west-2:1234567891011:job-queue/addf-sfn-example-core-batch-compute-FargateJobQueue"
    os.environ["SEEDFARMER_PARAMETER_DESIRED_ENCODING"] = "bgr8"
    os.environ["SEEDFARMER_PARAMETER_EMR_APP_ID"] = "00fgnvtcju9kd50l"
    os.environ[
        "SEEDFARMER_PARAMETER_SPOT_JOB_QUEUE_ARN"
    ] = "arn:aws:batch:us-west-2:1234567891011:job-queue/addf-sfn-example-core-batch-compute-SpotJobQueue"
    os.environ[
        "SEEDFARMER_PARAMETER_FULL_ACCESS_POLICY_ARN"
    ] = "arn:aws:iam::1234567891011:policy/addf-sfn-example-optionals-datalake-buckets-us-west-2-1234567891011-full-access"
    os.environ[
        "SEEDFARMER_PARAMETER_PARQUET_BATCH_JOB_DEF_ARN"
    ] = "arn:aws:batch:us-west-2:1234567891011:job-definition/addf-sfn-example-docker-images-ros-to-parquet:1"
    os.environ[
        "SEEDFARMER_PARAMETER_LANE_DETECTION_IMAGE_URI"
    ] = "1234567891011.dkr.ecr.us-west-2.amazonaws.com/addf-sfn-example-docker-images-lane-detection:smprocessor"
    os.environ["SEEDFARMER_PARAMETER_LOGS_BUCKET_NAME"] = "addf-sfn-example-logs-bucket-foobar"
    os.environ[
        "SEEDFARMER_PARAMETER_PRIVATE_SUBNET_IDS"
    ] = '"subnet-0d0dbcc18be75a515,subnet-0975db0ff8077da32,subnet-04672aec504dd73d3"'
    os.environ["SEEDFARMER_PARAMETER_SOURCE_BUCKET"] = "addf-sfn-example-raw-bucket-foobar"
    os.environ["SEEDFARMER_PARAMETER_VPC_ID"] = "vpc-0e166bcb8665cad2f"
    os.environ[
        "SEEDFARMER_PARAMETER_ON_DEMAND_JOB_QUEUE_ARN"
    ] = "arn:aws:batch:us-west-2:1234567891011:job-queue/addf-sfn-example-core-batch-compute-OnDemandJobQueue"
    os.environ[
        "SEEDFARMER_PARAMETER_OBJECT_DETECTION_IAM_ROLE"
    ] = "arn:aws:iam::1234567891011:role/addf-sfn-example-docker-i-addfsfnexampledockerimage-mhcRyBLGyJmc"
    os.environ["SEEDFARMER_PARAMETER_OBJECT_DETECTION_JOB_CONCURRENCY"] = "30"
    os.environ["SEEDFARMER_PARAMETER_ARTIFACTS_BUCKET"] = "addf-sfn-example-artifacts-bucket-foobar"
    os.environ["SEEDFARMER_PARAMETER_ARTIFACTS_BUCKET_NAME"] = "addf-sfn-example-artifacts-bucket-foobar"

    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401


def test_missing_argument(stack_defaults):

    with pytest.raises(ValueError) as e:
        import app  # noqa: F401

        os.environ["SEEDFARMER_PARAMETER_SOURCE_BUCKET"] = ""
        app.get_arg_value("SOURCE_BUCKET")


def test_project_deployment_name_length(stack_defaults):
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project-incredibly"

    with pytest.raises(Exception) as e:
        import app  # noqa: F401
    assert "module cannot support a project+deployment name character length greater than" in str(e)
