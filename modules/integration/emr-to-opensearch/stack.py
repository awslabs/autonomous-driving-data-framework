# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, List, cast

import cdk_nag
from aws_cdk import Aspects, Duration, Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_notifications as s3n
from aws_cdk.aws_lambda_python_alpha import PythonFunction, PythonLayerVersion
from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class EMRtoOpensearch(Stack):
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
        logs_bucket_name: str,
        emr_logs_prefix: str,
        **kwargs: Any,
    ) -> None:

        super().__init__(
            scope, id, description="This stack integrates EMR Cluster with Opensearch cluster for ADDF", **kwargs
        )
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

        os_security_group = ec2.SecurityGroup.from_security_group_id(self, f"{dep_mod}-os-sg", opensearch_sg_id)

        # Import Shared Logs bucket
        logs_bucket = s3.Bucket.from_bucket_name(self, f"{dep_mod}-logs-bucket", logs_bucket_name)

        emr_os_lambda_policy = iam.PolicyDocument(
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
                        "s3:ListBucket",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=[f"arn:aws:s3:::{logs_bucket_name}"],
                ),
                iam.PolicyStatement(
                    actions=[
                        "s3:GetObject",
                        "s3:GetObjectAcl",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=[f"arn:aws:s3:::{logs_bucket_name}/{emr_logs_prefix}*"],
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
            ]
        )

        emr_os_lambda_role = iam.Role(
            self,
            f"{dep_mod}-lambda-role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("lambda.amazonaws.com"),
            ),
            inline_policies={"EMRtoOSPolicyDocument": emr_os_lambda_policy},
        )

        requests_awsauth_layer = PythonLayerVersion(
            self,
            id=f"{dep_mod}-requests-aws4auth",
            entry="layers/",
            layer_version_name=f"{dep_mod}-requests-aws4auth",
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_7],
        )

        lambda_trigger = PythonFunction(
            self,
            "EMRlogstoOSTriggerLambda",
            entry="lambda",
            runtime=lambda_.Runtime.PYTHON_3_7,
            index="index.py",
            handler="handler",
            timeout=Duration.minutes(1),
            security_groups=[os_security_group],
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=self.private_subnets),
            environment={"REGION": self.region, "ACCOUNT": self.account, "DOMAIN_ENDPOINT": opensearch_domain_endpoint},
            role=emr_os_lambda_role,
            layers=[requests_awsauth_layer],
        )

        logs_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,  # Event
            s3n.LambdaDestination(lambda_trigger),  # Dest
            s3.NotificationKeyFilter(prefix=emr_logs_prefix, suffix="stderr.gz"),  # Prefix
        )

        logs_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,  # Event
            s3n.LambdaDestination(lambda_trigger),  # Dest
            s3.NotificationKeyFilter(prefix=emr_logs_prefix, suffix="controller.gz"),  # Prefix
        )

        self.lambda_name = lambda_trigger.function_name
        self.lambda_arn = lambda_trigger.function_arn

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
            ],
        )
