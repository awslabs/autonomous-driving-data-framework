# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

import aws_cdk
from aws_cdk import App, CfnOutput

from stack import MetadataStorageStack

# Project vars
project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


# App Env vars
scene_suffix = os.getenv(_param("ROSBAG_SCENE_TABLE_SUFFIX"))
if not scene_suffix:
    raise ValueError("ROSBAG_SCENE_TABLE_SUFFIX is not populated ")

glue_db_suffix = os.getenv(_param("GLUE_DB_SUFFIX"))
if not glue_db_suffix:
    raise ValueError("GLUE_DB_SUFFIX is not populated")

bagfile_suffix = os.getenv(_param("ROSBAG_BAGFILE_TABLE_SUFFIX"))
if not bagfile_suffix:
    raise ValueError("ROSBAG_BAGFILE_TABLE_SUFFIX is not populated")


def generate_description() -> str:
    soln_id = os.getenv(_param("SOLUTION_ID"), None)
    soln_name = os.getenv(_param("SOLUTION_NAME"), None)
    soln_version = os.getenv(_param("SOLUTION_VERSION"), None)

    desc = f"{project_name} - Metadata Storage Module"
    if soln_id and soln_name and soln_version:
        desc = f"({soln_id}) {soln_name}. Version {soln_version}"
    elif soln_id and soln_name:
        desc = f"({soln_id}) {soln_name}"
    return desc


app = App()

stack = MetadataStorageStack(
    scope=app,
    id=f"{project_name}-{deployment_name}-{module_name}",
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
    project_name=project_name,
    deployment_name=deployment_name,
    module_name=module_name,
    scene_table_suffix=scene_suffix,
    bagfile_table_suffix=bagfile_suffix,
    glue_db_suffix=glue_db_suffix,
    stack_description=generate_description(),
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "RosbagBagFileTable": stack.rosbag_bagfile_table.table_name,
            "RosbagBagFilePartitionKey": stack.rosbag_bagfile_partition_key,
            "RosbagSceneMetadataTable": stack.rosbag_scene_table.table_name,
            "RosbagSceneMetadataStreamArn": stack.rosbag_scene_table_stream_arn,
            "RosbagSceneMetadataPartitionKey": stack.rosbag_scene_p_key,
            "RosbagSceneMetadataSortKey": stack.rosbag_scene_sort_key,
            "GlueDBName": stack.glue_db.database_name,
        }
    ),
)


app.synth(force=True)
