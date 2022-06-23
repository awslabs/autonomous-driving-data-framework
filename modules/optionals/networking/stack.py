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
from typing import Any, List, cast

import aws_cdk.aws_ec2 as ec2
import cdk_nag
from aws_cdk import Aspects, Stack, Tags
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class NetworkingStack(Stack):  # type: ignore
    def __init__(self, scope: Construct, id: str, **kwargs: Any) -> None:
        self.deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME")
        self.internet_accessible = os.getenv("ADDF_PARAMETER_INTERNET_ACCESSIBLE", True)
        super().__init__(scope, id, **kwargs)
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{self.deployment_name}")
        self.vpc: ec2.Vpc = self._create_vpc()

        self.public_subnets = (
            self.vpc.select_subnets(subnet_type=ec2.SubnetType.PUBLIC)
            if self.vpc.public_subnets
            else self.vpc.select_subnets(subnet_group_name="")
        )
        self.private_subnets = (
            self.vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT)  # type: ignore
            if self.vpc.private_subnets
            else self.vpc.select_subnets(subnet_group_name="")
        )
        if not self.internet_accessible:
            self.isolated_subnets = (
                self.vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT)  # type: ignore
                if self.vpc.isolated_subnets
                else self.vpc.select_subnets(subnet_group_name="")
            )
            self.nodes_subnets = self.isolated_subnets
        else:
            self.nodes_subnets = self.private_subnets

        self._vpc_security_group = ec2.SecurityGroup(
            self, "vpc-sg", vpc=cast(ec2.IVpc, self.vpc), allow_all_outbound=False
        )
        # Adding ingress rule to VPC CIDR
        self._vpc_security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block), connection=ec2.Port.all_tcp()
        )

        # Creating Gateway Endpoints
        vpc_gateway_endpoints = {
            "s3": ec2.GatewayVpcEndpointAwsService.S3,
            "dynamodb": ec2.GatewayVpcEndpointAwsService.DYNAMODB,
        }

        for name, gateway_vpc_endpoint_service in vpc_gateway_endpoints.items():
            self.vpc.add_gateway_endpoint(
                id=name,
                service=gateway_vpc_endpoint_service,
                subnets=[
                    ec2.SubnetSelection(subnets=self.nodes_subnets.subnets),
                ],
            )

        if not self.internet_accessible:
            self._create_vpc_endpoints()

    def _create_vpc(self) -> ec2.Vpc:
        if self.internet_accessible:
            subnet_configuration = [
                ec2.SubnetConfiguration(name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
                ec2.SubnetConfiguration(
                    name="Private", subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT, cidr_mask=21  # type: ignore
                ),
            ]
        else:
            subnet_configuration = [
                ec2.SubnetConfiguration(name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
                ec2.SubnetConfiguration(
                    name="Private", subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT, cidr_mask=21  # type: ignore
                ),
                ec2.SubnetConfiguration(
                    name="Isolated", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=21  # type: ignore
                ),
            ]

        vpc = ec2.Vpc(
            scope=self,
            id="vpc",
            default_instance_tenancy=ec2.DefaultInstanceTenancy.DEFAULT,
            cidr="10.0.0.0/16",
            enable_dns_hostnames=True,
            enable_dns_support=True,
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=subnet_configuration,
        )

        # Enabling subnets for deploying Load Balancers via EKS
        NetworkingStack._tag_subnets(vpc.private_subnets, "kubernetes.io/role/internal-elb")
        NetworkingStack._tag_subnets(vpc.public_subnets, "kubernetes.io/role/elb")

        return vpc

    @staticmethod
    def _tag_subnets(subnets: List[ec2.ISubnet], tag: str) -> None:
        for subnet in subnets:
            Tags.of(subnet).add(tag, "1")

    def _create_vpc_endpoints(self) -> None:

        vpc_interface_endpoints = {
            "cloudwatch_endpoint": ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH,
            "cloudwatch_logs_endpoint": ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            "cloudwatch_events": ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_EVENTS,
            "ecr_docker_endpoint": ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
            "ecr_endpoint": ec2.InterfaceVpcEndpointAwsService.ECR,
            "ec2_endpoint": ec2.InterfaceVpcEndpointAwsService.EC2,
            "ecs": ec2.InterfaceVpcEndpointAwsService.ECS,
            "ecs_agent": ec2.InterfaceVpcEndpointAwsService.ECS_AGENT,
            "ecs_telemetry": ec2.InterfaceVpcEndpointAwsService.ECS_TELEMETRY,
            "git_endpoint": ec2.InterfaceVpcEndpointAwsService.CODECOMMIT_GIT,
            "ssm_endpoint": ec2.InterfaceVpcEndpointAwsService.SSM,
            "ssm_messages_endpoint": ec2.InterfaceVpcEndpointAwsService.SSM_MESSAGES,
            "secrets_endpoint": ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            "kms_endpoint": ec2.InterfaceVpcEndpointAwsService.KMS,
            "sagemaker_endpoint": ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_API,
            "sagemaker_runtime": ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_RUNTIME,
            "notebook_endpoint": ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_NOTEBOOK,
            "athena_endpoint": ec2.InterfaceVpcEndpointAwsService("athena"),
            "glue_endpoint": ec2.InterfaceVpcEndpointAwsService("glue"),
            "sqs": ec2.InterfaceVpcEndpointAwsService.SQS,
            "step_function_endpoint": ec2.InterfaceVpcEndpointAwsService("states"),
            "sns_endpoint": ec2.InterfaceVpcEndpointAwsService.SNS,
            "kinesis_firehose_endpoint": ec2.InterfaceVpcEndpointAwsService("kinesis-firehose"),
            "api_gateway": ec2.InterfaceVpcEndpointAwsService.APIGATEWAY,
            "sts_endpoint": ec2.InterfaceVpcEndpointAwsService.STS,
            "efs": ec2.InterfaceVpcEndpointAwsService.ELASTIC_FILESYSTEM,
            "elb": ec2.InterfaceVpcEndpointAwsService.ELASTIC_LOAD_BALANCING,
            "autoscaling": ec2.InterfaceVpcEndpointAwsService("autoscaling"),
            "cloudformation_endpoint": ec2.InterfaceVpcEndpointAwsService("cloudformation"),
            "codebuild_endpoint": ec2.InterfaceVpcEndpointAwsService("codebuild"),
            "emr-containers": ec2.InterfaceVpcEndpointAwsService("emr-containers"),
            "databrew": ec2.InterfaceVpcEndpointAwsService("databrew"),
        }

        for name, interface_service in vpc_interface_endpoints.items():
            self.vpc.add_interface_endpoint(
                id=name,
                service=interface_service,
                subnets=ec2.SubnetSelection(subnets=self.nodes_subnets.subnets),
                private_dns_enabled=True,
                security_groups=[cast(ec2.ISecurityGroup, self._vpc_security_group)],
            )
        # Adding CodeArtifact VPC endpoints
        self.vpc.add_interface_endpoint(
            id="code_artifact_repo_endpoint",
            service=cast(
                ec2.IInterfaceVpcEndpointService,
                ec2.InterfaceVpcEndpointAwsService("codeartifact.repositories"),
            ),
            subnets=ec2.SubnetSelection(subnets=self.nodes_subnets.subnets),
            private_dns_enabled=False,
            security_groups=[cast(ec2.ISecurityGroup, self._vpc_security_group)],
        )
        self.vpc.add_interface_endpoint(
            id="code_artifact_api_endpoint",
            service=cast(
                ec2.IInterfaceVpcEndpointService,
                ec2.InterfaceVpcEndpointAwsService("codeartifact.api"),
            ),
            subnets=ec2.SubnetSelection(subnets=self.nodes_subnets.subnets),
            private_dns_enabled=False,
            security_groups=[cast(ec2.ISecurityGroup, self._vpc_security_group)],
        )

        # Adding Lambda and Redshift endpoints with CDK low level APIs
        endpoint_url_template = "com.amazonaws.{}.{}"
        ec2.CfnVPCEndpoint(
            self,
            "redshift_endpoint",
            vpc_endpoint_type="Interface",
            service_name=endpoint_url_template.format(self.region, "redshift"),
            vpc_id=self.vpc.vpc_id,
            security_group_ids=[self._vpc_security_group.security_group_id],
            subnet_ids=self.nodes_subnets.subnet_ids,
            private_dns_enabled=True,
        )
        ec2.CfnVPCEndpoint(
            self,
            "lambda_endpoint",
            vpc_endpoint_type="Interface",
            service_name=endpoint_url_template.format(self.region, "lambda"),
            vpc_id=self.vpc.vpc_id,
            security_group_ids=[self._vpc_security_group.security_group_id],
            subnet_ids=self.nodes_subnets.subnet_ids,
            private_dns_enabled=True,
        )

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())
