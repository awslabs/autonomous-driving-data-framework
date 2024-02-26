# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, List, cast

import cdk_nag
from aws_cdk import Aspects, Duration, Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk.aws_lambda_python_alpha import PythonFunction, PythonLayerVersion
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class DDBtoOpensearch(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment: str,
        module: str,
        vpc_id: str,
        private_subnet_ids: List[str],
        opensearch_sg_id: str,
        opensearch_domain_endpoint: str,
        opensearch_domain_name: str,
        ddb_stream_arn: str,
        stack_description: str,
        **kwargs: Any,
    ) -> None:

        super().__init__(scope, id, description=stack_description, **kwargs)

        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{deployment}")

        dep_mod = f"addf-{deployment}-{module}"
        self.vpc_id = vpc_id
        self.vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=vpc_id,
        )

        self.private_subnets = []
        for idx, subnet_id in enumerate(private_subnet_ids):
            self.private_subnets.append(ec2.Subnet.from_subnet_id(scope=self, id=f"subnet{idx}", subnet_id=subnet_id))

        os_security_group = ec2.SecurityGroup.from_security_group_id(
            self, f"{dep_mod}-os-sg", opensearch_sg_id, allow_all_outbound=True
        )

        ddb_os_lambda_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "es:ESHttpPost",
                        "es:ESHttpPut",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=[f"arn:aws:es:{self.region}:{self.account}:domain/{opensearch_domain_name}*"],
                ),
                iam.PolicyStatement(
                    actions=[
                        "dynamodb:DescribeStream",
                        "dynamodb:GetRecords",
                        "dynamodb:GetShardIterator",
                        "dynamodb:ListStreams",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=[ddb_stream_arn],
                ),
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
                    resources=[f"arn:aws:logs:{self.region}:{self.account}:log-group:*"],
                ),
                iam.PolicyStatement(
                    actions=["ec2:Create*", "ec2:Delete*", "ec2:Describe*"],
                    effect=iam.Effect.ALLOW,
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    actions=["sts:AssumeRole"],
                    effect=iam.Effect.ALLOW,
                    resources=[f"arn:aws:iam::{self.account}:role/addf-*"],
                ),
            ]
        )

        ddb_os_lambda_role = iam.Role(
            self,
            f"{dep_mod}-lambda-role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("lambda.amazonaws.com"),
            ),
            inline_policies={"DDBtoOSPolicyDocument": ddb_os_lambda_policy},
        )

        requests_awsauth_layer = PythonLayerVersion(
            self,
            id=f"{dep_mod}-requests-aws4auth",
            entry="layers/",
            layer_version_name=f"{dep_mod}-requests-aws4auth",
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
        )

        lambda_trigger = PythonFunction(
            self,
            "DDBtoOSTriggerLambda",
            entry="lambda",
            runtime=lambda_.Runtime.PYTHON_3_9,
            index="index.py",
            handler="handler",
            timeout=Duration.minutes(1),
            security_groups=[os_security_group],
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=self.private_subnets),
            environment={"REGION": self.region, "ACCOUNT": self.account, "DOMAIN_ENDPOINT": opensearch_domain_endpoint},
            role=ddb_os_lambda_role,
            layers=[requests_awsauth_layer],
        )

        lambda_trigger.add_event_source_mapping(
            f"{dep_mod}-RosbagMetadataMapping",
            event_source_arn=ddb_stream_arn,
            starting_position=lambda_.StartingPosition.TRIM_HORIZON,
            batch_size=10,
        )

        self.lambda_name = lambda_trigger.function_name
        self.lambda_arn = lambda_trigger.function_arn

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
            ],
        )
