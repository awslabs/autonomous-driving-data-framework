# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, cast

import aws_cdk.aws_iam as iam
import cdk_nag
from aws_cdk import Aspects, Stack, Tags
from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class DagIamRole(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment_name: str,
        module_name: str,
        mwaa_exec_role: str,
        raw_bucket_name: str,
        **kwargs: Any,
    ) -> None:
        # ADDF Env vars
        self.deployment_name = deployment_name
        self.module_name = module_name
        self.mwaa_exec_role = mwaa_exec_role

        super().__init__(scope, id, description="This stack deploys Example Spark DAGs resources for ADDF", **kwargs)
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{deployment_name}")

        # The below permissions is to deploy the `citibike` usecase declared in the below blogpost
        # https://aws.amazon.com/blogs/big-data/manage-and-process-your-big-data-workflows-with-amazon-mwaa-and-amazon-emr-on-amazon-eks/
        policy_statements = [
            iam.PolicyStatement(
                actions=["s3:ListBucket", "s3:GetObject*"],
                effect=iam.Effect.ALLOW,
                resources=["arn:aws:s3:::tripdata", "arn:aws:s3:::tripdata/*"],
            ),
            iam.PolicyStatement(
                actions=["s3:*"],
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:aws:s3:::{raw_bucket_name}",
                    f"arn:aws:s3:::{raw_bucket_name}/*",
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "emr-containers:StartJobRun",
                    "emr-containers:ListJobRuns",
                    "emr-containers:DescribeJobRun",
                    "emr-containers:CancelJobRun",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=["kms:Decrypt", "kms:GenerateDataKey"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:kms:{self.region}:{self.account}:key/*"],
            ),
        ]
        dag_document = iam.PolicyDocument(statements=policy_statements)

        r_name = f"addf-{self.deployment_name}-{self.module_name}-dag-role"
        self.dag_role = iam.Role(
            self,
            f"dag-role-{self.deployment_name}-{self.module_name}",
            assumed_by=iam.ArnPrincipal(self.mwaa_exec_role),
            inline_policies={"DagPolicyDocument": dag_document},
            role_name=r_name,
            path="/",
        )

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            [
                {  # type: ignore
                    "id": "AwsSolutions-IAM5",
                    "reason": "Resource access restriced describe only",
                },
            ],
        )
