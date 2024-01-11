# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, cast

import aws_cdk
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_iam as iam
import cdk_nag
from aws_cdk import Aspects, Stack, Tags
from aws_cdk.aws_s3_assets import Asset
from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class ProxyStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment: str,
        module: str,
        vpc_id: str,
        opensearch_sg_id: str,
        opensearch_domain_endpoint: str,
        install_script: str,
        username: str,
        password: str,
        **kwargs: Any,
    ) -> None:

        super().__init__(
            scope,
            id,
            description="This stack deploys Proxy environment to access Opensearch dashboard for ADDF",
            **kwargs,
        )
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{deployment}")

        dep_mod = f"addf-{deployment}-{module}"
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
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443),
            "allow HTTPS traffic from anywhere",
        )

        # AMI
        amzn_linux = ec2.MachineImage.latest_amazon_linux(
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            edition=ec2.AmazonLinuxEdition.STANDARD,
            virtualization=ec2.AmazonLinuxVirt.HVM,
            storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE,
        )

        os_proxy_document = iam.PolicyDocument(
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
                    resources=[f"arn:aws:iam::{account}:role/addf-*"],
                ),
            ]
        )

        os_proxy_role = iam.Role(
            self,
            "os_proxy_role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("ec2.amazonaws.com"),
            ),
            inline_policies={"CDKosproxyPolicyDocument": os_proxy_document},
        )

        os_proxy_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))

        instance = ec2.Instance(
            self,
            "OSProxy",
            instance_type=ec2.InstanceType("t2.micro"),
            machine_image=amzn_linux,
            vpc=self.vpc,
            security_group=os_security_group,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            role=os_proxy_role,
        )

        asset = Asset(self, "Asset", path=install_script)
        local_path = instance.user_data.add_s3_download_command(bucket=asset.bucket, bucket_key=asset.s3_object_key)

        args = opensearch_domain_endpoint + " " + username + " " + password

        instance.user_data.add_execute_file_command(file_path=local_path, arguments=args)
        asset.grant_read(instance.role)

        self.instance_public_ip = instance.instance_public_ip
        self.instance_dns = instance.instance_public_dns_name
        url = f"https://{self.instance_dns}/_dashboards/"
        self.dashboard_url = url

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            apply_to_nested_stacks=True,
            suppressions=[
                {  # type: ignore
                    "id": "AwsSolutions-IAM4",
                    "reason": "Managed Policies are for service account roles only",
                },
                {  # type: ignore
                    "id": "AwsSolutions-IAM5",
                    "reason": "Resource access restriced to ADDF resources",
                },
                {  # type: ignore
                    "id": "AwsSolutions-EC23",
                    "reason": "Access is using basic-auth challenge",
                },
                {  # type: ignore
                    "id": "AwsSolutions-EC28",
                    "reason": "Detailed Monitoring not enabled as this is a simple proxy",
                },
                {  # type: ignore
                    "id": "AwsSolutions-EC29",
                    "reason": "ASG not enabled as this is a simple proxy",
                },
            ],
        )
