# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, List, cast

import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_iam as iam
import cdk_nag
from aws_cdk import Aspects, Duration, RemovalPolicy, Stack, Tags
from aws_cdk import aws_dynamodb as dynamo
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class AwsBatchPipeline(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment_name: str,
        module_name: str,
        vpc_id: str,
        mwaa_exec_role: str,
        bucket_access_policy: str,
        object_detection_role: str,
        lane_detection_role: str,
        job_queues: List[str],
        job_definitions: List[str],
        stack_description: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            scope,
            id,
            description=stack_description,
            **kwargs,
        )

        self.deployment_name = deployment_name
        self.module_name = module_name
        self.vpc_id = vpc_id
        self.mwaa_exec_role = mwaa_exec_role
        self.bucket_access_policy = bucket_access_policy

        Tags.of(scope=cast(IConstruct, self)).add(
            key="Deployment",
            value="aws",
        )

        dep_mod = f"addf-{self.deployment_name}-{self.module_name}"

        # DYNAMODB TRACKING TABLE
        self.tracking_table_name = f"{dep_mod}-drive-tracking"
        tracking_partition_key = "pk"  # batch_id or drive_id
        tracking_sort_key = "sk"  # batch_id / array_index_id   or drive_id / file_part

        dynamo.Table(
            self,
            self.tracking_table_name,
            table_name=self.tracking_table_name,
            partition_key=dynamo.Attribute(name=tracking_partition_key, type=dynamo.AttributeType.STRING),
            sort_key=dynamo.Attribute(name=tracking_sort_key, type=dynamo.AttributeType.STRING),
            billing_mode=dynamo.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True,
            stream=dynamo.StreamViewType.NEW_AND_OLD_IMAGES,
        )

        # Create Dag IAM Role and policy
        policy_statements = [
            iam.PolicyStatement(
                actions=["dynamodb:*"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:dynamodb:{self.region}:{self.account}:table/{dep_mod}*"],
            ),
            iam.PolicyStatement(
                actions=["ecr:*"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:ecr:{self.region}:{self.account}:repository/{dep_mod}*"],
            ),
            iam.PolicyStatement(
                actions=[
                    "batch:UntagResource",
                    "batch:DeregisterJobDefinition",
                    "batch:TerminateJob",
                    "batch:CancelJob",
                    "batch:SubmitJob",
                    "batch:RegisterJobDefinition",
                    "batch:TagResource",
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    *job_queues,
                    *job_definitions,
                    f"arn:aws:batch:{self.region}:{self.account}:job/*",
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "iam:PassRole",
                ],
                effect=iam.Effect.ALLOW,
                resources=[x for x in [object_detection_role, lane_detection_role] if x is not None],
            ),
            iam.PolicyStatement(
                actions=[
                    "batch:Describe*",
                    "batch:List*",
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    "*",
                ],
            ),
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:GetObjectAcl", "s3:ListBucket"],
                effect=iam.Effect.ALLOW,
                resources=["arn:aws:s3:::addf-*", "arn:aws:s3:::addf-*/*"],
            ),
        ]
        dag_document = iam.PolicyDocument(statements=policy_statements)

        dag_role_name = f"{dep_mod}-dag-{self.region}"

        self.dag_role = iam.Role(
            self,
            f"dag-role-{dep_mod}",
            assumed_by=iam.CompositePrincipal(
                iam.ArnPrincipal(self.mwaa_exec_role),
            ),
            inline_policies={"DagPolicyDocument": dag_document},
            managed_policies=[
                iam.ManagedPolicy.from_managed_policy_arn(
                    self, id="fullaccess", managed_policy_arn=self.bucket_access_policy
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
            ],
            role_name=dag_role_name,
            max_session_duration=Duration.hours(12),
            path="/",
        )

        # Sagemaker Security Group
        self.vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=self.vpc_id,
        )
        self.sm_sg = ec2.SecurityGroup(
            self,
            "SagemakerJobsSG",
            vpc=self.vpc,
            allow_all_outbound=True,
            description="Sagemaker Processing Jobs SG",
        )

        self.sm_sg.add_ingress_rule(peer=self.sm_sg, connection=ec2.Port.all_traffic())

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
