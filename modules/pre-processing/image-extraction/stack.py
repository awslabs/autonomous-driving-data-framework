# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from typing import Any, Optional, cast

import aws_cdk.aws_batch_alpha as batch
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_iam as iam
from aws_cdk import Aspects, Duration, Stack, Tags
from aws_cdk import aws_events as events
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_stepfunctions as stepfunctions
from aws_cdk import aws_stepfunctions_tasks as step_functions_tasks
from aws_cdk.aws_ecr_assets import DockerImageAsset
from aws_solutions_constructs.aws_s3_stepfunctions import S3ToStepfunctions
from cdk_ecr_deployment import DockerImageName, ECRDeployment
from cdk_nag import AwsSolutionsChecks, NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class ImageExtraction(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        project_name: str,
        deployment_name: str,
        module_name: str,
        repository_name: str,
        artifacts_bucket_name: str,
        platform: str,  # FARGATE or EC2
        retries: int,
        timeout_seconds: int,
        vcpus: int,
        memory_limit_mib: int,
        on_demand_job_queue_arn: str,
        start_range: Optional[str] = None,
        end_range: Optional[str] = None,
        **kwargs: Any,  # type: ignore
    ) -> None:
        super().__init__(
            scope,
            id,
            **kwargs,
        )

        dep_mod = f"{project_name}-{deployment_name}-{module_name}"
        # used to tag AWS resources. Tag Value length cant exceed 256 characters
        full_dep_mod = dep_mod[:256] if len(dep_mod) > 256 else dep_mod
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=full_dep_mod)

        # Build ImageExtraction Docker Image
        repo = ecr.Repository.from_repository_name(
            self, id=full_dep_mod + repository_name, repository_name=repository_name
        )

        local_image = DockerImageAsset(
            self,
            "ImageExtractionDockerImage",
            directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"),
        )

        image_uri = f"{repo.repository_uri}:latest"
        ECRDeployment(
            self,
            "ImageURI",
            src=DockerImageName(local_image.image_uri),
            dest=DockerImageName(image_uri),
        )

        policy_statements = [
            iam.PolicyStatement(
                actions=["ecr:*"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:{self.partition}:ecr:{self.region}:{self.account}:repository/{dep_mod}*"],
            ),
            iam.PolicyStatement(
                actions=["s3:ListAllMyBuckets"],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=["s3:ListBucket", "s3:GetBucketLocation"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:{self.partition}:s3:::{project_name}-*"],
            ),
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:GetObjectAcl",
                    "s3:PutObject",
                    "s3:PutObjectAcl",
                    "s3:DeleteObject",
                ],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:{self.partition}:s3:::{project_name}-*/*"],
            ),
        ]
        policy_document = iam.PolicyDocument(statements=policy_statements)

        role = iam.Role(
            self,
            f"{repository_name}-batch-role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            ),
            inline_policies={"ExtractionPolicyDocument": policy_document},
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy"),
            ],
            max_session_duration=Duration.hours(12),
        )

        # Build ImageExtraction AWS Batch Job Definition
        self.batch_job = batch.JobDefinition(
            self,
            "batch-job-defintion-from-ecr",
            container=batch.JobDefinitionContainer(
                image=ecs.ContainerImage.from_ecr_repository(repo, "latest"),
                environment={
                    "AWS_DEFAULT_REGION": self.region,
                    "AWS_ACCOUNT_ID": self.account,
                    "DEBUG": "true",
                },
                job_role=role,
                execution_role=role,
                memory_limit_mib=memory_limit_mib,
                vcpus=vcpus,
                privileged=True,
            ),
            job_definition_name=repository_name,
            platform_capabilities=[
                batch.PlatformCapabilities.FARGATE if platform == "FARGATE" else batch.PlatformCapabilities.EC2
            ],
            retry_attempts=retries,
            timeout=Duration.seconds(timeout_seconds),
        )

        # Invoke AWS Batch in Step Functions context
        submit_image_extraction_job = step_functions_tasks.BatchSubmitJob(
            self,
            f"{dep_mod}-Batchjob",
            job_name=f"{project_name}-image-extraction-job",
            job_queue_arn=on_demand_job_queue_arn,
            job_definition_arn=self.batch_job.job_definition_arn,
            container_overrides=step_functions_tasks.BatchContainerOverrides(
                environment={
                    "ARTIFACTS_BUCKET": stepfunctions.JsonPath.string_at("$.detail.bucket.name"),
                    "KEY": stepfunctions.JsonPath.string_at("$.detail.object.key"),
                    # "START_RANGE": start_range,
                    # "END_RANGE": end_range,
                },
            ),
            state_name="Image Extraction Batch Job",
        )

        succeed_job = stepfunctions.Succeed(self, "Succeeded", comment="AWS Batch Job succeeded")

        # Create Chain
        definition = submit_image_extraction_job.next(succeed_job)

        # Trigger StepFunction for S3 Events
        S3ToStepfunctions(
            self,
            "S3ToStepFunctions",
            existing_bucket_obj=s3.Bucket.from_bucket_name(self, "importedbucket", bucket_name=artifacts_bucket_name),
            event_rule_props=events.RuleProps(
                event_pattern=events.EventPattern(
                    source=["aws.s3"],
                    detail_type=["Object Created"],
                    detail={
                        "bucket": {"name": [artifacts_bucket_name]},
                        "object": {"key": [{"suffix": ".jsq"}]},
                    },
                )
            ),
            state_machine_props=stepfunctions.StateMachineProps(
                definition=definition,
                state_machine_name=f"{deployment_name}-{module_name}-S3FileProcessing",
            ),
        )

        self.role = role
        self.image_uri = image_uri

        Aspects.of(self).add(AwsSolutionsChecks())

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
                        "reason": f"Resource access restriced to {project_name} resources",
                    }
                ),
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-SF1",
                        "reason": "Step Function does not need to log ALL events to CloudWatch Logs",
                    }
                ),
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-SF2",
                        "reason": "Step Function does not need to have X Ray tracing enabled",
                    }
                ),
            ],
        )
