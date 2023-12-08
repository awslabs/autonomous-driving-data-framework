# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any, List, cast

from aws_cdk import Aspects, Duration, Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_emrserverless as emrserverless
from aws_cdk import aws_iam as iam
from cdk_nag import AwsSolutionsChecks, NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct


class EmrServerlessStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        project_name: str,
        deployment_name: str,
        module_name: str,
        vpc_id: str,
        private_subnet_ids: List[str],
        stack_description: str,
        **kwargs: Any,
    ) -> None:

        super().__init__(scope, id, description=stack_description, **kwargs)

        self.project_name = project_name
        self.deployment_name = deployment_name
        self.module_name = module_name
        self.vpc_id = vpc_id
        self.private_subnet_ids = private_subnet_ids

        dep_mod = f"{self.project_name}-{self.deployment_name}-{self.module_name}"
        dep_mod = dep_mod[:64]
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=dep_mod)

        self.vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=vpc_id,
        )

        self.emr_security_group = ec2.SecurityGroup(
            self,
            "EmrServerlessSG",
            vpc=self.vpc,
            allow_all_outbound=True,
            security_group_name=f"{self.project_name}-{self.deployment_name}-{self.module_name}-emr-s-sg",
        )

        self.emr_app = emrserverless.CfnApplication(
            self,
            f"{dep_mod}-emr-app",
            release_label="emr-6.8.0",
            type="Spark",
            auto_start_configuration=emrserverless.CfnApplication.AutoStartConfigurationProperty(enabled=True),
            auto_stop_configuration=emrserverless.CfnApplication.AutoStopConfigurationProperty(
                enabled=True, idle_timeout_minutes=5
            ),
            maximum_capacity=emrserverless.CfnApplication.MaximumAllowedResourcesProperty(
                cpu="100vCPU",
                memory="100GB",
                # the properties below are optional
                disk="1000GB",
            ),
            network_configuration=emrserverless.CfnApplication.NetworkConfigurationProperty(
                security_group_ids=[self.emr_security_group.security_group_id], subnet_ids=self.private_subnet_ids
            ),
            name=dep_mod,
        )

        policy_statements = [
            iam.PolicyStatement(
                actions=["dynamodb:*"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:dynamodb:{self.region}:{self.account}:table/{self.project_name}*"],
            ),
            iam.PolicyStatement(
                actions=["s3:*"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:s3:::{self.project_name}-*", f"arn:aws:s3:::{self.project_name}-*/*"],
            ),
        ]
        iam_policy = iam.PolicyDocument(statements=policy_statements)

        self.job_role = iam.Role(
            self,
            f"{dep_mod}-emr-job-role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("emr-serverless.amazonaws.com"),
            ),
            inline_policies={"DagPolicyDocument": iam_policy},
            max_session_duration=Duration.hours(12),
        )

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
                        "reason": "Resource access restriced to resources",
                    }
                ),
            ],
        )
