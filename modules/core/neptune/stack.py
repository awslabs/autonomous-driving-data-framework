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
from typing import Any, List, cast

import aws_cdk.aws_ec2 as ec2
import cdk_nag
from aws_cdk import Aspects, Duration, RemovalPolicy, Stack, Tags
from aws_cdk import aws_neptune_alpha as neptune
from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class NeptuneStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment: str,
        module: str,
        vpc_id: str,
        private_subnet_ids: List[str],
        number_instances: int,
        **kwargs: Any,
    ) -> None:

        dep_mod = f"addf-{deployment}-{module}"
        dep_mod = dep_mod[:27]

        # CDK Env Vars
        # account: str = aws_cdk.Aws.ACCOUNT_ID
        # region: str = aws_cdk.Aws.REGION

        super().__init__(scope, id, **kwargs)
        # Tagging all resources
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{deployment}")

        # Importing the VPC
        self.vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=vpc_id,
        )

        self.private_subnets = []
        for idx, subnet_id in enumerate(private_subnet_ids):
            self.private_subnets.append(ec2.Subnet.from_subnet_id(scope=self, id=f"subnet{idx}", subnet_id=subnet_id))

        sg_graph_db = ec2.SecurityGroup(
            self,
            f"{dep_mod}NeptuneSG",
            vpc=self.vpc,
            allow_all_outbound=True,
            description=f"{dep_mod} Security Group for Cluster",
            security_group_name=f"{dep_mod}-sg",
        )

        sg_graph_db.add_ingress_rule(peer=sg_graph_db, connection=ec2.Port.tcp(8182), description="Neptune Ingress")

        sg_graph_db.connections.allow_from(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(8182),
            "allow HTTPS traffic from anywhere",
        )

        cluster_params = neptune.ClusterParameterGroup(
            self,
            f"{dep_mod}ClusterParams",
            description="Cluster parameter group",
            parameters={"neptune_enable_audit_log": "1"},
        )

        db_params = neptune.ParameterGroup(
            self, "DbParams", description="Db parameter group", parameters={"neptune_query_timeout": "120000"}
        )

        subnet_group = neptune.SubnetGroup(
            self,
            f"{dep_mod}SubnetGroup",
            vpc=self.vpc,
            description="Some Description",
            removal_policy=RemovalPolicy.DESTROY,
            vpc_subnets=ec2.SubnetSelection(subnets=self.private_subnets),
        )

        cluster = neptune.DatabaseCluster(
            self,
            f"{dep_mod}DBCluster",
            vpc=self.vpc,
            db_cluster_name=f"{dep_mod}Cluster",
            instance_type=neptune.InstanceType.R5_LARGE,
            backup_retention=Duration.days(7),
            cluster_parameter_group=cluster_params,
            parameter_group=db_params,
            instances=number_instances,
            subnet_group=subnet_group,
            preferred_backup_window="08:45-09:15",
            preferred_maintenance_window="sun:18:00-sun:18:30",
            auto_minor_version_upgrade=True,
            security_groups=[sg_graph_db],
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.cluster = cluster
        self.sg_graph_db = sg_graph_db

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            apply_to_nested_stacks=True,
            suppressions=[
                {
                    "id": "AwsSolutions-N5",
                    "reason": "Cluster is in private subnets, no DB IAM auth enabled",
                    "applies_to": "*",
                },
                {
                    "id": "AwsSolutions-EC23",
                    "reason": "Cluster is in private subnets, open to all available IP within VPC",
                    "applies_to": "*",
                },
            ],
        )
