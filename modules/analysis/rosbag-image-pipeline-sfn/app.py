# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os
from typing import List, cast

from aws_cdk import App, CfnOutput, Environment

from stack import TemplateStack

# Project specific
project_name = os.getenv("SEEDFARMER_PROJECT_NAME")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME")
module_name = os.getenv("SEEDFARMER_MODULE_NAME")
hash = os.getenv("SEEDFARMER_HASH", "")

if len(f"{project_name}-{deployment_name}") > 36:
    raise ValueError("This module cannot support a project+deployment name character length greater than 35")


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


vpc_id = os.getenv(_param("VPC_ID"))
private_subnet_ids = json.loads(os.getenv(_param("PRIVATE_SUBNET_IDS")))

emr_job_exec_role_arn = os.getenv(_param("EMR_JOB_EXEC_ROLE"))
emr_app_id = os.getenv(_param("EMR_APP_ID"))

source_bucket_name = os.getenv(_param("SOURCE_BUCKET"))
target_bucket_name = os.getenv(_param("INTERMEDIATE_BUCKET"))
artifacts_bucket_name = os.getenv(_param("ARTIFACTS_BUCKET_NAME"))

detection_ddb_name = os.getenv(_param("ROSBAG_SCENE_METADATA_TABLE"))
on_demand_job_queue_arn = os.getenv(_param("ON_DEMAND_JOB_QUEUE_ARN"))
fargate_job_queue_arn = os.getenv(_param("FARGATE_JOB_QUEUE_ARN"))
parquet_batch_job_def_arn = os.getenv(_param("PARQUET_BATCH_JOB_DEF_ARN"))
png_batch_job_def_arn = os.getenv(_param("PNG_BATCH_JOB_DEF_ARN"))

object_detection_image_uri = os.getenv(_param("OBJECT_DETECTION_IMAGE_URI"))
object_detection_role = os.getenv(_param("OBJECT_DETECTION_IAM_ROLE"))
object_detection_job_concurrency = int(os.getenv(_param("OBJECT_DETECTION_JOB_CONCURRENCY"), 10))
object_detection_instance_type = os.getenv(_param("OBJECT_DETECTION_INSTANCE_TYPE"), "ml.m5.xlarge")

lane_detection_image_uri = os.getenv(_param("LANE_DETECTION_IMAGE_URI"))
lane_detection_role = os.getenv(_param("LANE_DETECTION_IAM_ROLE"))
lane_detection_job_concurrency = int(os.getenv(_param("LANE_DETECTION_JOB_CONCURRENCY"), 5))
lane_detection_instance_type = os.getenv(_param("LANE_DETECTION_INSTANCE_TYPE"), "ml.p3.2xlarge")

file_suffix = os.getenv(_param("FILE_SUFFIX"), ".bag")
desired_encoding = os.getenv(_param("DESIRED_ENCODING"), "bgr8")
yolo_model = os.getenv(_param("YOLO_MODEL"), "yolov5s")
image_topics: List[str] = json.loads(os.getenv(_param("IMAGE_TOPICS")))
sensor_topics: List[str] = json.loads(os.getenv(_param("SENSOR_TOPICS")))

if not isinstance(image_topics, list):
    raise ValueError("image_topics must be a list")

if not isinstance(sensor_topics, list):
    raise ValueError("sensor_topics must be a list")


def generate_description() -> str:
    soln_id = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_ID", None)
    soln_name = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_NAME", None)
    soln_version = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_VERSION", None)

    desc = "My Module Default Description"
    if soln_id and soln_name and soln_version:
        desc = f"({soln_id}) {soln_name}. Version {soln_version}"
    elif soln_id and soln_name:
        desc = f"({soln_id}) {soln_name}"
    return desc


app = App()

template_stack = TemplateStack(
    scope=app,
    id=f"{project_name}-{deployment_name}-{module_name}",
    project_name=cast(str, project_name),
    deployment_name=cast(str, deployment_name),
    module_name=cast(str, module_name),
    hash=cast(str, hash),
    stack_description=generate_description(),
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
    vpc_id=vpc_id,
    private_subnet_ids=private_subnet_ids,
    emr_job_exec_role_arn=emr_job_exec_role_arn,
    emr_app_id=emr_app_id,
    source_bucket_name=source_bucket_name,
    target_bucket_name=target_bucket_name,
    artifacts_bucket_name=artifacts_bucket_name,
    detection_ddb_name=detection_ddb_name,
    on_demand_job_queue_arn=on_demand_job_queue_arn,
    fargate_job_queue_arn=fargate_job_queue_arn,
    parquet_batch_job_def_arn=parquet_batch_job_def_arn,
    png_batch_job_def_arn=png_batch_job_def_arn,
    object_detection_image_uri=object_detection_image_uri,
    object_detection_role_arn=object_detection_role,
    object_detection_job_concurrency=object_detection_job_concurrency,
    object_detection_instance_type=object_detection_instance_type,
    lane_detection_image_uri=lane_detection_image_uri,
    lane_detection_role_arn=lane_detection_role,
    lane_detection_job_concurrency=lane_detection_job_concurrency,
    lane_detection_instance_type=lane_detection_instance_type,
    file_suffix=file_suffix,
    desired_encoding=desired_encoding,
    yolo_model=yolo_model,
    image_topics=image_topics,
    sensor_topics=sensor_topics,
)


CfnOutput(
    scope=template_stack,
    id="metadata",
    value=template_stack.to_json_string(
        {
            "TemplateOutput1": "Add something from template_stack",
        }
    ),
)

app.synth()
