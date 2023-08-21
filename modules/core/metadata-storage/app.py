# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

import aws_cdk
from aws_cdk import App, CfnOutput

from stack import MetadataStorageStack

# ADDF vars
deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


scene_suffix = os.getenv("ADDF_PARAMETER_ROSBAG_SCENE_TABLE_SUFFIX")
if not scene_suffix:
    raise ValueError("ADDF_PARAMETER_ROSBAG_SCENE_TABLE_SUFFIX not populated ")

glue_db_suffix = os.getenv("ADDF_PARAMETER_GLUE_DB_SUFFIX")
if not glue_db_suffix:
    raise ValueError("ADDF_PARAMETER_GLUE_DB_SUFFIX not populated")

bagfile_suffix = os.getenv("ADDF_PARAMETER_ROSBAG_BAGFILE_TABLE_SUFFIX")
if not bagfile_suffix:
    raise ValueError("ADDF_PARAMETER_ROSBAG_BAGFILE_TABLE_SUFFIX not populated")


app = App()

stack = MetadataStorageStack(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
    deployment=deployment_name,
    module=module_name,
    scene_table_suffix=scene_suffix,
    bagfile_table_suffix=bagfile_suffix,
    glue_db_suffix=glue_db_suffix,
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
