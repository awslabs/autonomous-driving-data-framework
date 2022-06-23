#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License").
#    You may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import logging
from typing import Any, cast

import cdk_nag
from aws_cdk import Aspects, RemovalPolicy, Stack, Tags
from aws_cdk import aws_dynamodb as dynamo
from aws_cdk import aws_glue_alpha as glue_alpha  # type: ignore
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class MetadataStorageStack(Stack):  # type: ignore
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment: str,
        module: str,
        scene_table_suffix: str,
        bagfile_table_suffix: str,
        glue_db_suffix: str,
        **kwargs: Any,
    ) -> None:

        dep_mod = f"addf-{deployment}-{module}"

        super().__init__(scope, id, **kwargs)
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{deployment}")

        rosbag_bagfile_p_key = "bag_file_prefix"
        rosbag_bagfile_table = dynamo.Table(
            self,
            "dynamobagfiletable",
            table_name=f"{dep_mod}-{bagfile_table_suffix}",
            partition_key=dynamo.Attribute(name=rosbag_bagfile_p_key, type=dynamo.AttributeType.STRING),
            billing_mode=dynamo.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True,
        )

        rosbag_scene_p_key = "bag_file"
        rosbag_scene_sort_key = "scene_id"
        rosbag_scene_table = dynamo.Table(
            self,
            "dynamotablescenes",
            table_name=f"{dep_mod}-{scene_table_suffix}",
            partition_key=dynamo.Attribute(name=rosbag_scene_p_key, type=dynamo.AttributeType.STRING),
            sort_key=dynamo.Attribute(name=rosbag_scene_sort_key, type=dynamo.AttributeType.STRING),
            billing_mode=dynamo.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True,
            stream=dynamo.StreamViewType.NEW_AND_OLD_IMAGES,
        )

        glue_db = glue_alpha.Database(
            self,
            "glue_db",
            database_name=f"{dep_mod}-{glue_db_suffix}",
        )

        self.rosbag_bagfile_table = rosbag_bagfile_table
        self.rosbag_bagfile_partition_key = rosbag_bagfile_p_key
        self.rosbag_scene_table = rosbag_scene_table
        self.rosbag_scene_table_stream_arn = rosbag_scene_table.table_stream_arn
        self.rosbag_scene_p_key = rosbag_scene_p_key
        self.rosbag_scene_sort_key = rosbag_scene_sort_key
        self.glue_db = glue_db

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks(verbose=True))
