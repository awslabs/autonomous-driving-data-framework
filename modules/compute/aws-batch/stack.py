# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, List, cast

import aws_cdk.aws_batch_alpha as batch
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_iam as iam
import cdk_nag
from aws_cdk import Aspects, Stack, Tags
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)

DEFAULT_MAX_VCPUS_PER_QUEUE = str(256)


class AwsBatch(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        project_name: str,
        deployment_name: str,
        module_name: str,
        vpc_id: str,
        private_subnet_ids: List[str],
        batch_compute: Dict[str, Any],
        stack_description: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            scope,
            id,
            description=stack_description,
            **kwargs,
        )

        dep_mod = f"{project_name}-{deployment_name}-{module_name}"

        # used to tag AWS resources. Tag Value length cant exceed 256 characters
        full_dep_mod = dep_mod[:256] if len(dep_mod) > 256 else dep_mod
        """
        dep_mod is used to name OpenSearch domain and the max length cant exceed 28 characters
        https://docs.aws.amazon.com/opensearch-service/latest/developerguide/createupdatedomains.html
        """

        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=full_dep_mod)

        self.vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=vpc_id,
        )

        self.private_subnets = []
        for idx, subnet_id in enumerate(private_subnet_ids):
            self.private_subnets.append(ec2.Subnet.from_subnet_id(scope=self, id=f"subnet{idx}", subnet_id=subnet_id))

        # Create IAM Policy for Airflow Dags to use Batch
        policy_statements = [
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
                    f"arn:aws:batch:{self.region}:{self.account}:job-queue/{project_name}*",
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
                    f"arn:aws:iam::{self.account}:role/{project_name}*",
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
        policy_document = iam.PolicyDocument(statements=policy_statements).to_string()

        batch_sg = ec2.SecurityGroup(self, "BatchSG", vpc=self.vpc, allow_all_outbound=True, description="Batch SG")

        batch_sg.add_egress_rule(ec2.Peer.ipv4(self.vpc.vpc_cidr_block), ec2.Port.all_tcp())

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
                    ebs_config = batchenv.get("ebs_config", {})
                    if ebs_config:

                        launch_template_name = "additional-storage-template"

                        ec2.CfnLaunchTemplate(
                            self,
                            "StorageLaunchTemplate",
                            launch_template_name=launch_template_name,
                            launch_template_data=ec2.CfnLaunchTemplate.LaunchTemplateDataProperty(
                                block_device_mappings=[
                                    ec2.CfnLaunchTemplate.BlockDeviceMappingProperty(
                                        device_name="/dev/xvda",
                                        ebs=ec2.CfnLaunchTemplate.EbsProperty(
                                            encrypted=True,
                                            delete_on_termination=True,
                                            iops=ebs_config["ebs_iops"],  # max iops of an m5.xlarge instance -
                                            # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/
                                            # ebs-optimized.html#ebs-optimization-support
                                            volume_size=ebs_config["ebs_size_gbs"],
                                            volume_type=ebs_config["ebs_type"],
                                        ),
                                    )
                                ],
                                metadata_options=ec2.CfnLaunchTemplate.MetadataOptionsProperty(
                                    http_endpoint="enabled", http_tokens="required", http_put_response_hop_limit=3
                                ),
                                ebs_optimized=True,
                                monitoring=ec2.CfnLaunchTemplate.MonitoringProperty(enabled=True),
                            ),
                        )
                        launch_template_spec = batch.LaunchTemplateSpecification(
                            launch_template_name=launch_template_name,
                        )
                    else:
                        launch_template_spec = None

                    if instance_types_context:
                        for value in instance_types_context:
                            instance_type = ec2.InstanceType(value)
                            instance_types.append(instance_type)
                    on_demand_compute_env = batch.ComputeEnvironment(
                        self,
                        f"{dep_mod}-OnDemandComputeEnv-{batchenv.get('env_name')}",
                        compute_resources=batch.ComputeResources(
                            vpc=self.vpc,
                            instance_types=instance_types if instance_types else None,
                            maxv_cpus=batchenv.get("max_vcpus", DEFAULT_MAX_VCPUS_PER_QUEUE),
                            minv_cpus=0,
                            launch_template=launch_template_spec,
                            type=batch.ComputeResourceType.ON_DEMAND,
                            vpc_subnets=ec2.SubnetSelection(subnets=self.private_subnets),
                            security_groups=[batch_sg],
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
                            vpc=self.vpc,
                            instance_types=instance_types if instance_types else None,
                            maxv_cpus=batchenv.get("max_vcpus", DEFAULT_MAX_VCPUS_PER_QUEUE),
                            minv_cpus=0,
                            type=batch.ComputeResourceType.SPOT,
                            vpc_subnets=ec2.SubnetSelection(subnets=self.private_subnets),
                            security_groups=[batch_sg],
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
                            vpc=self.vpc,
                            maxv_cpus=batchenv.get("max_vcpus", DEFAULT_MAX_VCPUS_PER_QUEUE),
                            type=batch.ComputeResourceType.FARGATE,
                            vpc_subnets=ec2.SubnetSelection(subnets=self.private_subnets),
                            security_groups=[batch_sg],
                        ),
                    )

                    fargate_compute_env_list.append(
                        batch.JobQueueComputeEnvironment(
                            compute_environment=fargate_compute_env, order=int(batchenv.get("order"))
                        )
                    )

        # Outputs
        self.on_demand_jobqueue = None
        if on_demand_compute_env_list:
            self.on_demand_jobqueue = batch.JobQueue(
                self,
                f"{dep_mod}-OndemandJobQueue",
                compute_environments=on_demand_compute_env_list,
                job_queue_name=f"{dep_mod}-OnDemandJobQueue",
                priority=1,
            )

        self.spot_jobqueue = None
        if spot_compute_env_list:
            self.spot_jobqueue = batch.JobQueue(
                self,
                f"{dep_mod}-SpotJobQueue",
                compute_environments=spot_compute_env_list,
                job_queue_name=f"{dep_mod}-SpotJobQueue",
                priority=1,
            )

        self.fargate_jobqueue = None
        if fargate_compute_env_list:
            self.fargate_jobqueue = batch.JobQueue(
                self,
                f"{dep_mod}-FargateJobQueue",
                compute_environments=fargate_compute_env_list,
                job_queue_name=f"{dep_mod}-FargateJobQueue",
                priority=1,
            )

        self.batch_sg = batch_sg.security_group_id
        self.batch_policy_document = policy_document

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
                        "reason": "Resource access restriced to IDF resources",
                    }
                ),
            ],
        )
