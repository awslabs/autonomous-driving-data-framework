# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, List, cast

import aws_cdk.aws_batch_alpha as batch
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_iam as iam
import cdk_nag
from aws_cdk import Aspects, Stack, Tags
from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class BatchDags(Stack):
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
        batch_compute: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        # ADDF Env vars
        self.deployment_name = deployment_name
        self.module_name = module_name
        self.mwaa_exec_role = mwaa_exec_role

        super().__init__(
            scope,
            id,
            description="(SO9154) Autonomous Driving Data Framework (ADDF) - batch-managed",
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

        # Create Dag IAM Role and policy
        policy_statements = [
            iam.PolicyStatement(
                actions=["sqs:*"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:sqs:{self.region}:{self.account}:{dep_mod}*"],
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
                    f"arn:aws:batch:{self.region}:{self.account}:job-queue/addf*",
                    f"arn:aws:batch:{self.region}:{self.account}:job-definition/*",
                    f"arn:aws:batch:{self.region}:{self.account}:job/*",
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "iam:PassRole",
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:aws:iam::{self.account}:role/addf*",
                ],
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
        ]
        dag_document = iam.PolicyDocument(statements=policy_statements)

        batch_role_name = f"{dep_mod}-dag-role"
        self.dag_role = iam.Role(
            self,
            f"dag-role-{dep_mod}",
            assumed_by=iam.CompositePrincipal(
                iam.ArnPrincipal(self.mwaa_exec_role), iam.ServicePrincipal("ecs-tasks.amazonaws.com")
            ),
            inline_policies={"DagPolicyDocument": dag_document},
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ],
            role_name=batch_role_name,
            path="/",
        )

        ec2Role = iam.Role(
            self,
            "BatchEC2Role",
            assumed_by=iam.CompositePrincipal(iam.ServicePrincipal("ec2.amazonaws.com")),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonEC2ContainerServiceforEC2Role"),
            ],
        )

        ec2IAMProfile = iam.CfnInstanceProfile(self, "BatchEC2RoleInstanceProfile", roles=[ec2Role.role_name])

        batchSG = ec2.SecurityGroup(self, "BatchSG", vpc=self.vpc, allow_all_outbound=True, description="Batch SG")

        batchSG.add_egress_rule(ec2.Peer.ipv4(self.vpc.vpc_cidr_block), ec2.Port.all_tcp())

        # Creates Compute Env conditionally
        batch_compute_config = batch_compute.get("batch_compute_config")
        on_demand_compute_env_list = []
        spot_compute_env_list = []
        fargate_compute_env_list = []
        if batch_compute_config:
            for batchenv in batch_compute_config:
                if batchenv.get("compute_type").upper().startswith("ON"):
                    instance_types_context = batchenv.get("instance_types")
                    instance_types = []
                    if instance_types_context:
                        for value in instance_types_context:
                            instance_type = ec2.InstanceType(value)
                            instance_types.append(instance_type)
                    on_demand_compute_env = batch.ComputeEnvironment(
                        self,
                        f"{dep_mod}-OnDemandComputeEnv-{batchenv.get('env_name')}",
                        compute_resources=batch.ComputeResources(
                            instance_role=ec2IAMProfile.attr_arn,
                            vpc=self.vpc,
                            instance_types=instance_types if instance_types else None,
                            maxv_cpus=batchenv.get("max_vcpus") if batchenv.get("max_vcpus") else "256",  # type: ignore
                            minv_cpus=0,
                            type=batch.ComputeResourceType.ON_DEMAND,
                            vpc_subnets=ec2.SubnetSelection(subnets=self.private_subnets),
                            security_groups=[batchSG],
                        ),
                    )
                    on_demand_compute_env_list.append(
                        batch.JobQueueComputeEnvironment(
                            compute_environment=on_demand_compute_env,
                            order=int(batchenv.get("order")),
                        )
                    )
                elif batchenv.get("compute_type").upper() == "SPOT":
                    instance_types_context = batchenv.get("instance_types")
                    instance_types = []
                    if instance_types_context:
                        for value in instance_types_context:
                            instance_type = ec2.InstanceType(value)
                            instance_types.append(instance_type)
                    spot_compute_env = batch.ComputeEnvironment(
                        self,
                        f"{dep_mod}-SpotComputeEnv-{batchenv.get('env_name')}",
                        compute_resources=batch.ComputeResources(
                            instance_role=ec2IAMProfile.attr_arn,
                            vpc=self.vpc,
                            instance_types=instance_types if instance_types else None,
                            maxv_cpus=batchenv.get("max_vcpus") if batchenv.get("max_vcpus") else "256",  # type: ignore
                            minv_cpus=0,
                            type=batch.ComputeResourceType.SPOT,
                            vpc_subnets=ec2.SubnetSelection(subnets=self.private_subnets),
                            security_groups=[batchSG],
                            allocation_strategy=batch.AllocationStrategy("SPOT_CAPACITY_OPTIMIZED"),
                        ),
                    )
                    spot_compute_env_list.append(
                        batch.JobQueueComputeEnvironment(
                            compute_environment=spot_compute_env,
                            order=int(batchenv.get("order")),
                        )
                    )
                else:
                    fargate_compute_env = batch.ComputeEnvironment(
                        self,
                        f"{dep_mod}-FargateJobEnv-{batchenv.get('env_name')}",
                        compute_resources=batch.ComputeResources(
                            type=batch.ComputeResourceType.FARGATE,
                            vpc_subnets=ec2.SubnetSelection(subnets=self.private_subnets),
                            vpc=self.vpc,
                        ),
                    )

                    fargate_compute_env_list.append(
                        batch.JobQueueComputeEnvironment(
                            compute_environment=fargate_compute_env, order=int(batchenv.get("order"))
                        )
                    )

        if on_demand_compute_env_list:
            self.on_demand_jobqueue = batch.JobQueue(
                self,
                f"{dep_mod}-OndemandJobQueue",
                compute_environments=on_demand_compute_env_list,
                job_queue_name=f"{dep_mod}-OnDemandJobQueue",
                priority=1,
            )

        if spot_compute_env_list:
            self.spot_jobqueue = batch.JobQueue(
                self,
                f"{dep_mod}-SpotJobQueue",
                compute_environments=spot_compute_env_list,
                job_queue_name=f"{dep_mod}-SpotJobQueue",
                priority=1,
            )

        if fargate_compute_env_list:
            self.fargate_jobqueue = batch.JobQueue(
                self,
                f"{dep_mod}-FargateJobQueue",
                compute_environments=fargate_compute_env_list,
                job_queue_name=f"{dep_mod}-FargateJobQueue",
                priority=1,
            )

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
