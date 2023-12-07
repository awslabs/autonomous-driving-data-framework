#!/usr/bin/env python3

# type: ignore

import json
import os
from typing import List

import aws_cdk

from infrastructure.ecs_stack import Fargate
from infrastructure.emr_launch.cluster_definition import EMRClusterDefinition
from infrastructure.emr_orchestration.stack import StepFunctionStack
from infrastructure.emr_trigger.stack import EmrTriggerStack

# ADDF
deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME")
module_name = os.getenv("ADDF_MODULE_NAME")
hash = os.getenv("ADDF_HASH")
# Module Metadata
vpc_id = os.getenv("ADDF_PARAMETER_VPC_ID")  # required
private_subnet_ids = json.loads(os.getenv("ADDF_PARAMETER_PRIVATE_SUBNET_IDS"))  # required
input_bucket_name = os.getenv("ADDF_PARAMETER_SOURCE_BUCKET_NAME")  # required
output_bucket_name = os.getenv("ADDF_PARAMETER_DESTINATION_BUCKET_NAME")  # required
logs_bucket_name = os.getenv("ADDF_PARAMETER_LOGS_BUCKET_NAME")  # required
artifact_bucket_name = os.getenv("ADDF_PARAMETER_ARTIFACT_BUCKET_NAME")  # required
retention_type = os.getenv("ADDF_PARAMETER_RETENTION_TYPE", "DESTROY")
glue_db_name = os.getenv("ADDF_PARAMETER_GLUE_DB_NAME")  # required
rosbag_bagfile_table = os.getenv("ADDF_PARAMETER_ROSBAG_BAGFILE_TABLE")  # required
rosbag_scene_metadata_table = os.getenv("ADDF_PARAMETER_ROSBAG_SCENE_METADATA_TABLE")  # required
rosbag_files_input_path_relative_to_s3 = os.getenv("ADDF_PARAMETER_ROSBAG_FILES_INPUT_PATH_RELATIVE_TO_S3")  # required
emr_config = json.loads(os.environ.get("ADDF_PARAMETER_EMR"))  # required
fargate_config = json.loads(os.environ.get("ADDF_PARAMETER_FARGATE"))  # required

if (
    not vpc_id
    and not private_subnet_ids
    and not input_bucket_name
    and not output_bucket_name
    and not logs_bucket_name
    and not artifact_bucket_name
    and not glue_db_name
    and not rosbag_bagfile_table
    and not rosbag_scene_metadata_table
    and not rosbag_files_input_path_relative_to_s3
    and not emr_config
    and not fargate_config
):
    raise ValueError("Missing the required input arguements to scene-detection module")

# Load config
project_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(project_dir, "config.json")
with open(config_file) as json_file:
    config = json.load(json_file)

app = aws_cdk.App()


def fargate(config):
    image_name = fargate_config["image-name"]
    ecr_repository_name = fargate_config["ecr-repository-name"]

    cpu = fargate_config["cpu"]
    memory_limit_mib = fargate_config["memory-limit-mib"]
    timeout_minutes = fargate_config["timeout-minutes"]
    s3_filters = config["s3-filters"]

    default_environment_vars = config["environment-variables"]
    topics_to_extract = ",".join(config["topics-to-extract"])

    fargate_stack = Fargate(
        app,
        id=f"addf-{deployment_name}-{module_name}",
        deployment_name=deployment_name,
        module_name=module_name,
        image_name=image_name,
        environment_vars=default_environment_vars,
        ecr_repository_name=ecr_repository_name,
        cpu=cpu,
        description="(SO9154) Autonomous Driving Data Framework (ADDF) - rosbag-scene-detection",
        memory_limit_mib=memory_limit_mib,
        timeout_minutes=timeout_minutes,
        s3_filters=s3_filters,
        input_bucket_name=input_bucket_name,
        output_bucket_name=output_bucket_name,
        vpc_id=vpc_id,
        private_subnet_ids=private_subnet_ids,
        topics_to_extract=topics_to_extract,
        glue_db_name=glue_db_name,
        rosbag_bagfile_table=rosbag_bagfile_table,
        rosbag_files_input_path_relative_to_s3=rosbag_files_input_path_relative_to_s3,
        env=aws_cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )

    return fargate_stack


def emr(input_buckets: List[str]):

    environment_variables = [
        "CLUSTER_NAME",
        "MASTER_INSTANCE_TYPE",
        "CORE_INSTANCE_TYPE",
        "CORE_INSTANCE_COUNT",
        "CORE_INSTANCE_MARKET",
        "TASK_INSTANCE_TYPE",
        "TASK_INSTANCE_COUNT",
        "TASK_INSTANCE_MARKET",
        "RELEASE_LABEL",
        "APPLICATIONS",
        "CONFIGURATION",
    ]

    clean_config = {
        "INPUT_BUCKETS": input_buckets,
        "module_name": module_name,
        "deployment_name": deployment_name,
        "hash": hash,
        "vpc_id": vpc_id,
        "private_subnet_ids": private_subnet_ids,
        "logs_bucket_name": logs_bucket_name,
        "artifact_bucket_name": artifact_bucket_name,
        "emr_bucket_retention_type": retention_type,
    }

    for v in environment_variables:
        val = emr_config[v]
        clean_config[v] = val

    return EMRClusterDefinition(
        app,
        id=f"addf-{deployment_name}-{module_name}-{emr_config['CLUSTER_NAME']}",
        config=clean_config,
        env=aws_cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )


fargate_stack = fargate(config["fargate"])

emr_cluster_stack = emr(input_buckets=[f"arn:aws:s3:::{output_bucket_name}"])

emr_orchestration_stack = StepFunctionStack(
    app,
    id=f"addf-{deployment_name}-{module_name}-emr-orchestration",
    deployment_name=deployment_name,
    module_name=module_name,
    emr_launch_stack=emr_cluster_stack,
    artifact_bucket=artifact_bucket_name,
    synchronized_bucket=emr_cluster_stack.synchronized_bucket,
    scenes_bucket=emr_cluster_stack.scenes_bucket,
    glue_db_name=glue_db_name,
    rosbag_scene_metadata_table=rosbag_scene_metadata_table,
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)


emr_trigger_stack = EmrTriggerStack(
    app,
    id=f"addf-{deployment_name}-{module_name}-emr-trigger",
    deployment_name=deployment_name,
    module_name=module_name,
    target_step_function_arn=emr_orchestration_stack.state_machine.state_machine_arn,
    source_bucket_sns=fargate_stack.new_files_topic,
    dynamo_table=emr_orchestration_stack.dynamo_table,
    num_rosbag_topics=len(config["fargate"]["topics-to-extract"]),
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)

app.synth()
