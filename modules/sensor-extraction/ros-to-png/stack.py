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
import os
import typing
from typing import Any, cast

import aws_cdk.aws_batch_alpha as batch
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_iam as iam
from aws_cdk import Duration, RemovalPolicy, Stack, Tags
from aws_cdk.aws_ecr_assets import DockerImageAsset
from cdk_ecr_deployment import DockerImageName, ECRDeployment
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class RosToPngBatchJob(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment_name: str,
        module_name: str,
        s3_access_policy: str,
        retries: int,
        timeout_seconds: int,
        vcpus: int,
        memory_limit_mib: int,
        resized_width: int,
        resized_height: int,
        removal_policy: RemovalPolicy = RemovalPolicy.RETAIN,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            scope,
            id,
            description="(SO9154) Autonomous Driving Data Framework (ADDF) - ros-to-png",
            **kwargs,
        )

        Tags.of(scope=cast(IConstruct, self)).add(
            key="Deployment",
            value="aws",
        )

        dep_mod = f"addf-{deployment_name}-{module_name}"

        self.repository_name = dep_mod
        repo = ecr.Repository(
            self, id=self.repository_name, repository_name=self.repository_name, removal_policy=removal_policy
        )

        local_image = DockerImageAsset(
            self,
            "RosToPng",
            directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"),
        )

        image_uri = f"{repo.repository_uri}:latest"
        ECRDeployment(
            self,
            "RosToPngURI",
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

        self.batch_job = batch.JobDefinition(
            self,
            "batch-job-def-from-ecr",
            container=batch.JobDefinitionContainer(
                image=ecs.ContainerImage.from_ecr_repository(repo, "latest"),
                command=["bash", "entrypoint.sh"],
                environment={
                    "AWS_DEFAULT_REGION": self.region,
                    "AWS_ACCOUNT_ID": self.account,
                    "DEBUG": "true",
                    "RESIZE_WIDTH": str(resized_width),
                    "RESIZE_HEIGHT": str(resized_height),
                },
                job_role=role,
                execution_role=role,
                memory_limit_mib=memory_limit_mib,
                vcpus=vcpus,
                volumes=[
                    ecs.Volume(
                        name="scratch",
                        docker_volume_configuration=ecs.DockerVolumeConfiguration(
                            scope=ecs.Scope.TASK, driver="local", labels={"scratch": "space"}
                        ),
                    ),
                ],
                mount_points=[
                    ecs.MountPoint(
                        source_volume="scratch",
                        container_path="/mnt/ebs",
                        read_only=False,
                    ),
                ],
            ),
            job_definition_name=self.repository_name,
            platform_capabilities=[batch.PlatformCapabilities.EC2],
            retry_attempts=retries,
            timeout=Duration.seconds(timeout_seconds),
        )
