# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os
from typing import List, Optional, cast

from aws_cdk import App, CfnOutput, Environment

from stack import TemplateStack

# Project specific
project_name = os.getenv("SEEDFARMER_PROJECT_NAME")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME")
module_name = os.getenv("SEEDFARMER_MODULE_NAME")
hash = os.getenv("SEEDFARMER_HASH", "")

if len(f"{project_name}-{deployment_name}") > 36:
    raise ValueError("This module cannot support a project+deployment name character length greater than 35")


def get_arg_value(name: str, default: Optional[str] = None) -> str:

    value = (
        os.getenv(f"SEEDFARMER_PARAMETER_{name}", default) if default else os.getenv(f"SEEDFARMER_PARAMETER_{name}", "")
    )
    if value == "":
        raise ValueError(f"required argument {name.replace('_', '-').lower()} is missing")
    else:
        return value


vpc_id = get_arg_value("VPC_ID")
private_subnet_ids = json.loads(get_arg_value("PRIVATE_SUBNET_IDS"))

emr_job_exec_role_arn = get_arg_value("EMR_JOB_EXEC_ROLE")
emr_app_id = get_arg_value("EMR_APP_ID")

source_bucket_name = get_arg_value("SOURCE_BUCKET")
target_bucket_name = get_arg_value("INTERMEDIATE_BUCKET")
artifacts_bucket_name = get_arg_value("ARTIFACTS_BUCKET_NAME")
logs_bucket_name = get_arg_value("LOGS_BUCKET_NAME")

detection_ddb_name = get_arg_value("ROSBAG_SCENE_METADATA_TABLE")
on_demand_job_queue_arn = get_arg_value("ON_DEMAND_JOB_QUEUE_ARN")
fargate_job_queue_arn = get_arg_value("FARGATE_JOB_QUEUE_ARN")
parquet_batch_job_def_arn = get_arg_value("PARQUET_BATCH_JOB_DEF_ARN")
png_batch_job_def_arn = get_arg_value("PNG_BATCH_JOB_DEF_ARN")

object_detection_image_uri = get_arg_value("OBJECT_DETECTION_IMAGE_URI")
object_detection_role = get_arg_value("OBJECT_DETECTION_IAM_ROLE")
object_detection_job_concurrency = int(get_arg_value("OBJECT_DETECTION_JOB_CONCURRENCY", "10"))
object_detection_instance_type = get_arg_value("OBJECT_DETECTION_INSTANCE_TYPE", "ml.m5.xlarge")

lane_detection_image_uri = get_arg_value("LANE_DETECTION_IMAGE_URI")
lane_detection_role = get_arg_value("LANE_DETECTION_IAM_ROLE")
lane_detection_job_concurrency = int(get_arg_value("LANE_DETECTION_JOB_CONCURRENCY", "5"))
lane_detection_instance_type = get_arg_value("LANE_DETECTION_INSTANCE_TYPE", "ml.p3.2xlarge")

file_suffix = get_arg_value("FILE_SUFFIX", ".bag")
desired_encoding = get_arg_value("DESIRED_ENCODING", "bgr8")
yolo_model = get_arg_value("YOLO_MODEL", "yolov5s")
image_topics: List[str] = json.loads(get_arg_value("IMAGE_TOPICS"))
sensor_topics: List[str] = json.loads(get_arg_value("SENSOR_TOPICS"))

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
    hash=hash,
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
    logs_bucket_name=logs_bucket_name,
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
            "StateMachineArn": template_stack.state_machine.state_machine_arn,
        }
    ),
)

app.synth()
