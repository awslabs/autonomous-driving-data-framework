# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, cast

import aws_cdk.aws_batch_alpha as batch
import aws_cdk.aws_iam as iam
from aws_cdk import Duration, NestedStack, Stack, Tags
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_events as events
from aws_cdk import aws_stepfunctions as stepfunctions
from aws_cdk import aws_stepfunctions_tasks as step_functions_tasks
from aws_solutions_constructs.aws_eventbridge_stepfunctions import EventbridgeToStepfunctions

# from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

# import cdk_nag


_logger: logging.Logger = logging.getLogger(__name__)


class EventDrivenBatch(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment_name: str,
        module_name: str,
        fargate_job_queue_arn: str,
        ecr_repo_name: str,
        vcpus: int,
        memory_limit_mib: int,
        **kwargs: Any,
    ) -> None:
        # ADDF Env vars
        self.deployment_name = deployment_name
        self.module_name = module_name

        super().__init__(
            scope,
            id,
            description="This stack deploys Cron Based Eventbridge which triggers Stepfunctions further triggering AWS Batch",  # noqa: E501
            **kwargs,
        )
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{deployment_name}")

        dep_mod = f"addf-{deployment_name}-{module_name}"

        # Batch Resources

        role = iam.Role(
            self,
            f"{dep_mod}-AWSBatchRole",
            assumed_by=iam.ServicePrincipal(service="ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_managed_policy_arn(
                    self,
                    "MetricsAmazonEC2ContainerRegistryReadOnly",
                    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
                ),
                iam.ManagedPolicy.from_managed_policy_arn(
                    self,
                    "MetricsAmazonEC2ContainerServiceforEC2Role",
                    "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role",
                ),
            ],
            inline_policies={
                "S3Read": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["s3:GetObject"],
                            resources=["*"],
                        )
                    ]
                )
            },
        )

        repository = ecr.Repository.from_repository_name(self, id=id, repository_name=f"{dep_mod}-{ecr_repo_name}")

        img = ecs.EcrImage.from_ecr_repository(repository=repository, tag="latest")

        definition = batch.JobDefinition(
            self,
            f"{dep_mod}-JobDefinition",
            job_definition_name=f"addf-{deployment_name}-Job-Definition",
            retry_attempts=1,
            platform_capabilities=[batch.PlatformCapabilities.FARGATE],
            container=batch.JobDefinitionContainer(
                environment={"AWS_REGION": NestedStack.of(self).region},
                vcpus=int(vcpus),
                memory_limit_mib=int(memory_limit_mib),
                execution_role=role,
                job_role=role,
                image=img,
                # command=["echo", "I ran fine"],
            ),
        )

        # Step functions Definition

        submit_metrics_job = step_functions_tasks.BatchSubmitJob(
            self,
            f"{dep_mod}-Batchjob",
            job_name=f"addf-{deployment_name}-Job",
            job_queue_arn=fargate_job_queue_arn,
            job_definition_arn=definition.job_definition_arn,
        )

        wait_job = stepfunctions.Wait(
            self, "Wait 30 Seconds", time=stepfunctions.WaitTime.duration(Duration.seconds(30))
        )

        # fail_job = stepfunctions.Fail(self, "Fail", cause="AWS Batch Job Failed", error="DescribeJob returned FAILED")

        succeed_job = stepfunctions.Succeed(self, "Succeeded", comment="AWS Batch Job succeeded")

        # Create Chain

        definition = submit_metrics_job.next(wait_job).next(succeed_job)  # type: ignore

        self.eventbridge_sfn = EventbridgeToStepfunctions(
            self,
            f"addf-{deployment_name}-eb-sf-batch",
            state_machine_props=stepfunctions.StateMachineProps(definition=definition),  # type: ignore
            event_rule_props=events.RuleProps(schedule=events.Schedule.rate(Duration.minutes(1))),
        )
