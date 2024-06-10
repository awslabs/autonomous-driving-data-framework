# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Optional, cast

import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_iam as iam
import cdk_nag
from aws_cdk import Aspects, Duration, RemovalPolicy, Stack, Tags
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class ObjectDetection(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        project_name: str,
        deployment_name: str,
        module_name: str,
        s3_access_policy: str,
        removal_policy: Optional[RemovalPolicy] = RemovalPolicy.DESTROY,
        stack_description: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            scope,
            id,
            description=stack_description,
            **kwargs,
        )

        Tags.of(scope=cast(IConstruct, self)).add(
            key="Deployment",
            value="aws",
        )

        dep_mod = f"{project_name}-{deployment_name}-{module_name}"

        self.repository_name = dep_mod

        repo = ecr.Repository(
            self,
            id=self.repository_name,
            repository_name=self.repository_name,
            removal_policy=removal_policy,
            auto_delete_images=True if removal_policy == RemovalPolicy.DESTROY else False,
        )

        self.image_uri = f"{repo.repository_uri}:latest"

        policy_statements = [
            iam.PolicyStatement(
                actions=["dynamodb:*"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:dynamodb:{self.region}:{self.account}:table/{project_name}*"],
            ),
            iam.PolicyStatement(
                actions=["ecr:*"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:ecr:{self.region}:{self.account}:repository/{dep_mod}*"],
            ),
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:GetObjectAcl", "s3:ListBucket"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:s3:::{project_name}-*", f"arn:aws:s3:::{project_name}-*/*"],
            ),
        ]
        dag_document = iam.PolicyDocument(statements=policy_statements)

        self.role = iam.Role(
            self,
            f"{self.repository_name}-sm-role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("sagemaker.amazonaws.com"),
            ),
            inline_policies={"DagPolicyDocument": dag_document},
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy"),
                iam.ManagedPolicy.from_managed_policy_arn(self, id="fullaccess", managed_policy_arn=s3_access_policy),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
            ],
            max_session_duration=Duration.hours(12),
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
            ],
        )
