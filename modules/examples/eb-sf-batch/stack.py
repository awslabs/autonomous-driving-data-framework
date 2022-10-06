import imp
import logging
from typing import Any, Dict, List, cast

import aws_cdk
import aws_cdk.aws_batch_alpha as batch
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_iam as iam
import cdk_nag
from aws_cdk import Aspects, Duration, Stack, Tags
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as events_targets
from aws_cdk import aws_stepfunctions as step_functions
from aws_cdk import aws_stepfunctions as stepfunctions
from aws_cdk import aws_stepfunctions_tasks as step_functions_tasks
from aws_solutions_constructs.aws_eventbridge_stepfunctions import (
    EventbridgeToStepfunctions,
    EventbridgeToStepfunctionsProps,
)
from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)
from constructs import Construct


class EventDrivenBatch(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment_name: str,
        module_name: str,
        mwaa_exec_role: str,
        vpc_id: str,
        private_subnet_ids: List[str],
        batch_compute: Dict[str, any],
        ecr_repo_name: str,
        **kwargs: Any,
    ) -> None:
        # ADDF Env vars
        self.deployment_name = deployment_name
        self.module_name = module_name
        self.mwaa_exec_role = mwaa_exec_role

        super().__init__(
            scope,
            id,
            description="This stack deploys Managed AWS Batch Compute environment(s) for simulations in ADDF",
            **kwargs,
        )
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{deployment_name}")

        dep_mod = f"addf-{deployment_name}-{module_name}"

        self.vpc_id = vpc_id
        self.vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=vpc_id,
        )

        self.private_subnets = []
        for idx, subnet_id in enumerate(private_subnet_ids):
            self.private_subnets.append(ec2.Subnet.from_subnet_id(scope=self, id=f"subnet{idx}", subnet_id=subnet_id))
        
        # Batch Resources

        role = iam.Role(
            self,
            "MetricsAWSBatchRole",
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

        repo = ecr.Repository.from_repository_name(self, id=id, repository_name=ecr_repo_name)

        img = ecs.EcrImage.from_ecr_repository(repository=repo, tag="latest")

        definition = batch.JobDefinition(
            self,
            "MetricsJobDefinition",
            job_definition_name="Metrics-Job-Definition",
            retry_attempts=1,
            container=batch.JobDefinitionContainer(
                environment={"AWS_REGION": NestedStack.of(self).region},
                vcpus=2,
                memory_limit_mib=4096,
                execution_role=role,
                job_role=role,
                image=img,
                command=["Ref::indexed_data_sources_bucket", "Ref::key"],
            ),
        )

        submit_metrics_job = step_functions_tasks.BatchSubmitJob(
            self,
            "Submit metrics calculation job",
            job_name="MetricsCalculation",
            job_queue_arn=metrics_job_queue.job_queue_arn,
            job_definition_arn=metrics_job_definition.job_definition_arn,
            payload=step_functions.TaskInput.from_object(
                {
                    "indexed_data_sources_bucket": step_functions.JsonPath.string_at(
                        "$.detail.requestParameters.bucketName"
                    ),
                    "key": step_functions.JsonPath.string_at("$.detail.requestParameters.key"),
                }
            ),
        )


        # Step Function
        startState = stepfunctions.Pass(self, "StartState")

        map_task = step_functions.State(self, 'Run analysis in parallel')\
            .branch(submit_metrics_job)\
            .branch(submit_errors_job)

        EventbridgeToStepfunctions(
            self,
            "test-eventbridge-stepfunctions-stack",
            state_machine_props=stepfunctions.StateMachineProps(definition=startState),
            event_rule_props=events.RuleProps(schedule=events.Schedule.rate(Duration.minutes(5))),
        )
