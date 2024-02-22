# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import logging
from typing import Any, cast

import aws_cdk
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_iam as iam
import cdk_nag
from aws_cdk import Aspects, Stack, Tags
from aws_cdk.aws_s3_assets import Asset
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class TunnelStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment: str,
        module: str,
        project_name: str,
        vpc_id: str,
        opensearch_sg_id: str,
        opensearch_domain_endpoint: str,
        install_script: str,
        port: int,
        stack_description: str,
        **kwargs: Any,
    ) -> None:

        super().__init__(
            scope,
            id,
            description=stack_description,
            **kwargs,
        )
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"{project_name}-{deployment}")

        dep_mod = f"{project_name}-{deployment}-{module}"
        # CDK Env Vars
        account: str = aws_cdk.Aws.ACCOUNT_ID
        region: str = aws_cdk.Aws.REGION

        self.vpc_id = vpc_id
        self.vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=vpc_id,
        )

        os_security_group = ec2.SecurityGroup.from_security_group_id(self, f"{dep_mod}-os-sg", opensearch_sg_id)

        os_security_group.connections.allow_from(
            ec2.Peer.ipv4(cidr_ip=self.vpc.vpc_cidr_block),
            ec2.Port.all_traffic(),
            "allow all traffic from VPC CIDR",
        )

        # AMI
        amzn_linux = ec2.MachineImage.latest_amazon_linux2023(
            edition=ec2.AmazonLinuxEdition.STANDARD,
        )

        os_tunnel_document = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "logs:CreateLogStream",
                        "logs:CreateLogGroup",
                        "logs:PutLogEvents",
                        "logs:GetLogEvents",
                        "logs:GetLogRecord",
                        "logs:GetLogGroupFields",
                        "logs:GetQueryResults",
                        "logs:DescribeLogGroups",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=[f"arn:aws:logs:{region}:{account}:log-group:*"],
                ),
                iam.PolicyStatement(
                    actions=["sts:AssumeRole"],
                    effect=iam.Effect.ALLOW,
                    resources=[f"arn:aws:iam::{account}:role/{project_name}-*"],
                ),
            ]
        )

        os_tunnel_role = iam.Role(
            self,
            "os_tunnel_role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("ec2.amazonaws.com"),
            ),
            inline_policies={"CDKostunnelPolicyDocument": os_tunnel_document},
        )

        os_tunnel_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
        )

        instance = ec2.Instance(
            self,
            "OSTunnel",
            instance_type=ec2.InstanceType("t2.micro"),
            require_imdsv2=True,
            machine_image=amzn_linux,
            vpc=self.vpc,
            security_group=os_security_group,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            role=os_tunnel_role,
            block_devices=[
                ec2.BlockDevice(device_name="/dev/xvda", volume=ec2.BlockDeviceVolume.ebs(10, encrypted=True))
            ],
        )

        asset = Asset(self, "Asset", path=install_script)
        local_path = instance.user_data.add_s3_download_command(bucket=asset.bucket, bucket_key=asset.s3_object_key)

        args = opensearch_domain_endpoint + " " + str(port)

        instance.user_data.add_execute_file_command(file_path=local_path, arguments=args)
        asset.grant_read(instance.role)

        self.instance_id = instance.instance_id
        url = f"http://localhost:{port}/_dashboards/"
        self.dashboard_url = url

        json_params = {"portNumber": [str(port)], "localPortNumber": [str(port)]}

        self.command = (
            f"aws ssm start-session --target {self.instance_id} "
            "--document-name AWS-StartPortForwardingSession "
            f"--parameters '{json.dumps(json_params)}'"
        )

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            apply_to_nested_stacks=True,
            suppressions=[
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-IAM4",
                        "reason": "Managed Policies are for service account roles only",
                    }
                ),
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-IAM5",
                        "reason": "Resource access restriced to ADDF resources",
                    }
                ),
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-EC23",
                        "reason": "Access is uin a private subnet",
                    }
                ),
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-EC28",
                        "reason": "Detailed Monitoring not enabled as this is a simple tunnel",
                    }
                ),
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-EC29",
                        "reason": "ASG not enabled as this is a simple tunnel",
                    }
                ),
            ],
        )
