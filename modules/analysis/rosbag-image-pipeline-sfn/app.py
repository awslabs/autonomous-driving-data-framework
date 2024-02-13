# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os

from aws_cdk import App, CfnOutput, Environment

from stack import AwsBatchPipeline

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


vpc_id = os.getenv(_param("VPC_ID"))
full_access_policy = os.getenv(_param("FULL_ACCESS_POLICY_ARN"))
source_bucket_name = os.getenv(_param("SOURCE_BUCKET"))
target_bucket_name = os.getenv(_param("INTERMEDIATE_BUCKET"))
artifacts_bucket_name = os.getenv(_param("ARTIFACTS_BUCKET_NAME"))
logs_bucket_name = os.getenv(_param("LOGS_BUCKET_NAME"))
detection_ddb_name = os.getenv(_param("ROSBAG_SCENE_METADATA_TABLE"))
on_demand_job_queue = os.getenv(_param("ON_DEMAND_JOB_QUEUE_ARN"))
spot_job_queue = os.getenv(_param("SPOT_JOB_QUEUE_ARN"))
fargate_job_queue = os.getenv(_param("FARGATE_JOB_QUEUE_ARN"))
parquet_batch_job_def_arn = os.getenv(_param("PARQUET_BATCH_JOB_DEF_ARN"))
png_batch_job_def_arn = os.getenv(_param("PNG_BATCH_JOB_DEF_ARN"))
object_detection_image_uri = os.getenv(_param("OBJECT_DETECTION_IMAGE_URI"))
object_detection_role = os.getenv(_param("OBJECT_DETECTION_IAM_ROLE"))
object_detection_job_concurrency = os.getenv(_param("OBJECT_DETECTION_JOB_CONCURRENCY"), 10)
object_detection_instance_type = os.getenv(_param("OBJECT_DETECTION_INSTANCE_TYPE"), "ml.m5.xlarge")

lane_detection_image_uri = os.getenv(_param("LANE_DETECTION_IMAGE_URI"))
lane_detection_role = os.getenv(_param("LANE_DETECTION_IAM_ROLE"))
lane_detection_job_concurrency = os.getenv(_param("LANE_DETECTION_JOB_CONCURRENCY"), 5)
lane_detection_instance_type = os.getenv(_param("LANE_DETECTION_INSTANCE_TYPE"), "ml.p3.2xlarge")

file_suffix = os.getenv(_param("FILE_SUFFIX"), ".bag")
desired_encoding = os.getenv(_param("DESIRED_ENCODING"), "bgr8")
yolo_model = os.getenv(_param("YOLO_MODEL"), "yolov5s")
image_topics = json.loads(os.getenv(_param("IMAGE_TOPICS")))
sensor_topics = json.loads(os.getenv(_param("SENSOR_TOPICS")))

emr_job_role = os.getenv(_param("EMR_JOB_EXEC_ROLE"))
emr_app_id = os.getenv(_param("EMR_APP_ID"))


if not artifacts_bucket_name:
    raise ValueError("missing input parameter artifacts-bucket-name")

if not logs_bucket_name:
    raise ValueError("missing input parameter logs-bucket-name")

if not target_bucket_name:
    raise ValueError("missing input parameter intermediate-bucket")

if not png_batch_job_def_arn:
    raise ValueError("missing input parameter png-batch-job-def-arn")

if not parquet_batch_job_def_arn:
    raise ValueError("missing input parameter parquet-batch-job-def-arn")

if not object_detection_role:
    raise ValueError("missing input parameter object-detection-iam-role")

if not object_detection_image_uri:
    raise ValueError("missing input parameter object-detection-image-uri")

if not lane_detection_role:
    raise ValueError("missing input parameter lane-detection-iam-role")

if not lane_detection_image_uri:
    raise ValueError("missing input parameter lane-detection-image-uri")

if not full_access_policy:
    raise ValueError("S3 Full Access Policy ARN is missing.")

if not vpc_id:
    raise ValueError("missing input parameter vpc-id")

if not on_demand_job_queue:
    raise ValueError("missing input parameter on-demand-job-queue-arn")

if not spot_job_queue:
    raise ValueError("missing input parameter spot-job-queue-arn")

if not fargate_job_queue:
    raise ValueError("missing input parameter fargate-job-queue-arn")

if not emr_app_id:
    raise ValueError("missing input parameter emr-app-id")

if not emr_job_role:
    raise ValueError("missing input parameter emr-job-role")


def generate_description() -> str:
    soln_id = os.getenv("ADDF_PARAMETER_SOLUTION_ID", None)
    soln_name = os.getenv("ADDF_PARAMETER_SOLUTION_NAME", None)
    soln_version = os.getenv("ADDF_PARAMETER_SOLUTION_VERSION", None)

    desc = "Autonomous Driving Data Framework (ADDF) - rosbag-image-pipeline-sfn"
    if soln_id and soln_name and soln_version:
        desc = f"({soln_id}) {soln_name}. Version {soln_version}"
    elif soln_id and soln_name:
        desc = f"({soln_id}) {soln_name}"
    return desc


app = App()

stack = AwsBatchPipeline(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    bucket_access_policy=full_access_policy,
    target_bucket_name=target_bucket_name,
    logs_bucket_name=logs_bucket_name,
    artifacts_bucket_name=artifacts_bucket_name,
    vpc_id=vpc_id,
    job_queues={
        "fargate_job_queue": fargate_job_queue,
        "spot_job_queue": spot_job_queue,
        "on_demand_job_queue": on_demand_job_queue,
    },
    job_definitions={
        "png_batch_job_def_arn": png_batch_job_def_arn,
        "parquet_batch_job_def_arn": parquet_batch_job_def_arn,
    },
    lane_detection_config={
        "LaneDetectionImageUri": lane_detection_image_uri,
        "LaneDetectionRole": lane_detection_role,
        "LaneDetectionJobConcurrency": lane_detection_job_concurrency,
        "LaneDetectionInstanceType": lane_detection_instance_type,
        "LaneDetectionRole": lane_detection_role,
    },
    object_detection_config={
        "ObjectDetectionImageUri": object_detection_image_uri,
        "ObjectDetectionRole": object_detection_role,
        "ObjectDetectionJobConcurrency": object_detection_job_concurrency,
        "ObjectDetectionInstanceType": object_detection_instance_type,
        "ObjectDetectionRole": object_detection_role,
    },
    emr_job_config={
        "EMRApplicationId": emr_app_id,
        "EMRJobRole": emr_job_role,
    },
    image_topics=image_topics,
    stack_description=generate_description(),
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "SecurityGroupId": stack.security_group.security_group_id,
            "SfnRoleArn": stack.sfn_role.role_arn,
            "DynamoDbTableName": stack.tracking_table_name,
            "DetectionsDynamoDBName": detection_ddb_name,
            "SourceBucketName": source_bucket_name,
            "TargetBucketName": target_bucket_name,
            "LogsBucketName": logs_bucket_name,
            "OnDemandJobQueueArn": on_demand_job_queue,
            "SpotJobQueueArn": spot_job_queue,
            "FargateJobQueueArn": fargate_job_queue,
            "ParquetBatchJobDefArn": parquet_batch_job_def_arn,
            "PngBatchJobDefArn": png_batch_job_def_arn,
            "ObjectDetectionImageUri": object_detection_image_uri,
            "ObjectDetectionRole": object_detection_role,
            "ObjectDetectionJobConcurrency": object_detection_job_concurrency,
            "ObjectDetectionInstanceType": object_detection_instance_type,
            "LaneDetectionImageUri": lane_detection_image_uri,
            "LaneDetectionRole": lane_detection_role,
            "LaneDetectionJobConcurrency": lane_detection_job_concurrency,
            "LaneDetectionInstanceType": lane_detection_instance_type,
            "FileSuffix": file_suffix,
            "DesiredEncoding": desired_encoding,
            "YoloModel": yolo_model,
            "ImageTopics": image_topics,
            "SensorTopics": sensor_topics,
        }
    ),
)

app.synth(force=True)
