# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from typing import Any, cast

import aws_cdk.aws_batch as batch
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_iam as iam
import cdk_nag
from aws_cdk import Aspects, Duration, RemovalPolicy, Size, Stack, Tags
from aws_cdk.aws_ecr_assets import DockerImageAsset
from cdk_ecr_deployment import DockerImageName, ECRDeployment
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class RosToParquetBatchJob(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment_name: str,
        module_name: str,
        s3_access_policy: str,
        platform: str,  # FARGATE or EC2
        retries: int,
        timeout_seconds: int,
        vcpus: int,
        memory_limit_mib: int,
        removal_policy: RemovalPolicy = RemovalPolicy.DESTROY,
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

        dep_mod = f"addf-{deployment_name}-{module_name}"

        self.repository_name = dep_mod
        repo = ecr.Repository(
            self,
            id=self.repository_name,
            repository_name=self.repository_name,
            removal_policy=removal_policy,
            auto_delete_images=True if removal_policy == RemovalPolicy.DESTROY else False,
        )

        local_image = DockerImageAsset(
            self,
            "RosToParquet",
            directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"),
        )

        image_uri = f"{repo.repository_uri}:latest"
        ECRDeployment(
            self,
            "RosToParquetURI",
            src=DockerImageName(local_image.image_uri),
            dest=DockerImageName(image_uri),
        )

        policy_statements = [
            iam.PolicyStatement(
                actions=["dynamodb:*"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:dynamodb:{self.region}:{self.account}:table/addf*"],
            ),
            iam.PolicyStatement(
                actions=["ecr:*"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:ecr:{self.region}:{self.account}:repository/{dep_mod}*"],
            ),
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:GetObjectAcl", "s3:ListBucket"],
                effect=iam.Effect.ALLOW,
                resources=["arn:aws:s3:::addf-*", "arn:aws:s3:::addf-*/*"],
            ),
        ]
        dag_document = iam.PolicyDocument(statements=policy_statements)

        role = iam.Role(
            self,
            f"{self.repository_name}-batch-role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            ),
            inline_policies={"DagPolicyDocument": dag_document},
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy"),
                iam.ManagedPolicy.from_managed_policy_arn(self, id="fullaccess", managed_policy_arn=s3_access_policy),
            ],
            max_session_duration=Duration.hours(12),
        )

        self.batch_job = batch.EcsJobDefinition(
            self,
            "batch-job-def-from-ecr",
            container=batch.EcsFargateContainerDefinition(  # type: ignore
                self,
                "batch-job-container-def",
                image=ecs.ContainerImage.from_ecr_repository(repo, "latest"),
                command=["bash", "entrypoint.sh"],
                environment={
                    "AWS_DEFAULT_REGION": self.region,
                    "AWS_ACCOUNT_ID": self.account,
                    "DEBUG": "true",
                },
                job_role=role,
                execution_role=role,
                memory=Size.mebibytes(memory_limit_mib),
                cpu=vcpus,
            )
            if platform == "FARGATE"
            else batch.EcsEc2ContainerDefinition(
                self,
                "batch-job-container-def",
                image=ecs.ContainerImage.from_ecr_repository(repo, "latest"),
                command=["bash", "entrypoint.sh"],
                environment={
                    "AWS_DEFAULT_REGION": self.region,
                    "AWS_ACCOUNT_ID": self.account,
                    "DEBUG": "true",
                },
                job_role=role,
                execution_role=role,
                memory=Size.mebibytes(memory_limit_mib),
                cpu=vcpus,
            ),
            job_definition_name=self.repository_name,
            retry_attempts=retries,
            timeout=Duration.seconds(timeout_seconds),
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
