# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from string import Template
from typing import Any, cast

import yaml
from aws_cdk import Duration, Environment, Stack, Tags
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_eks as eks
from aws_cdk import aws_iam as iam
from aws_cdk import aws_sqs as sqs
from aws_cdk.aws_ecr_assets import DockerImageAsset
from aws_cdk.lambda_layer_kubectl_v29 import KubectlV29Layer
from cdk_ecr_deployment import DockerImageName, ECRDeployment
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct

project_dir = os.path.dirname(os.path.abspath(__file__))

ROLE_NAME = "addf-eureka-simulation-role"
APPLICATION_IMAGE_NAME = "ubuntu-ros2"


class EurekaStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        project_name: str,
        deployment_name: str,
        module_name: str,
        stack_description: str,
        eks_cluster_name: str,
        eks_cluster_admin_role_arn: str,
        eks_oidc_arn: str,
        eks_cluster_open_id_connect_issuer: str,
        simulation_data_bucket_name: str,
        sqs_name: str,
        fsx_volume_handle: str,
        fsx_mount_point: str,
        application_ecr_name: str,
        env: Environment,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id, description=stack_description, **kwargs)

        self.project_name = project_name
        self.deployment_name = deployment_name
        self.module_name = module_name

        dep_mod = f"{self.project_name}-{self.deployment_name}-{self.module_name}"
        dep_mod = dep_mod[:64]
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=dep_mod)

        provider = eks.OpenIdConnectProvider.from_open_id_connect_provider_arn(
            self, f"{dep_mod}-provider", eks_oidc_arn
        )
        eks_cluster = eks.Cluster.from_cluster_attributes(
            self,
            f"{dep_mod}-eks-cluster",
            cluster_name=eks_cluster_name,
            kubectl_role_arn=eks_cluster_admin_role_arn,
            open_id_connect_provider=provider,
            kubectl_layer=KubectlV29Layer(self, "Kubectlv29Layer"),
        )
        manifest = self.get_fsx_static_provisioning_manifest(fsx_volume_handle, fsx_mount_point, env)
        manifest_file = list(yaml.load_all(manifest, Loader=yaml.FullLoader))
        loop_iteration = 0
        for value in manifest_file:
            loop_iteration = loop_iteration + 1
            manifest_id = "Eureka" + str(loop_iteration)
            eks_cluster.add_manifest(manifest_id, value)

        self.iam_role_arn = self.create_simulation_role(
            eks_cluster_open_id_connect_issuer,
            eks_oidc_arn,
            simulation_data_bucket_name,
        )
        self.sqs_url = self.create_sqs(sqs_name, env)
        self.application_image_uri = self.build_application_image(application_ecr_name)
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

    def create_simulation_role(
        self,
        eks_cluster_open_id_connect_issuer: str,
        eks_oidc_arn: str,
        simulation_data_bucket_name: str,
    ) -> str:
        role = iam.Role(
            self,
            ROLE_NAME,
            assumed_by=iam.FederatedPrincipal(
                eks_oidc_arn,
                {"StringLike": {f"{eks_cluster_open_id_connect_issuer}:sub": "system:serviceaccount:*"}},
                "sts:AssumeRoleWithWebIdentity",
            ),
        )
        role.add_to_principal_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:AbortMultipartUpload",
                    "s3:ListBucket",
                    "s3:GetObjectVersion",
                    "s3:ListMultipartUploadParts",
                ],
                resources=[
                    f"arn:{self.paritition}:s3:::${simulation_data_bucket_name}/*",
                    f"arn:{self.paritition}:s3:::${simulation_data_bucket_name}",
                ],
            )
        )

        role.add_to_principal_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sqs:*",
                    "fsx:CreateFileSystem",
                    "fsx:DeleteFileSystem",
                    "fsx:DescribeFileSystems",
                    "fsx:TagResource",
                ],
                resources=["*"],
            )
        )

        role.add_to_principal_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:ListFoundationModels",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:InvokeModel",
                    "bedrock:InvokeAgent",
                ],
                resources=["*"],
            )
        )
        role.add_to_principal_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "iam:CreateServiceLinkedRole",
                    "iam:AttachRolePolicy",
                    "iam:PutRolePolicy",
                ],
                resources=[f"arn:{self.paritition}:iam::*:role/aws-service-role/s3.data-source.lustre.fsx.amazonaws.com/*"],
            )
        )
        fsx_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "iam:CreateServiceLinkedRole",
            ],
            resources=["*"],
        )
        fsx_policy.add_conditions({"StringLike": {"iam:AWSServiceName": ["fsx.amazonaws.com"]}})
        role.add_to_principal_policy(fsx_policy)
        return role.role_arn

    def build_application_image(self, application_ecr_name: str) -> str:
        local_image = DockerImageAsset(
            self,
            "ImageExtractionDockerImage",
            directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"),
        )
        repo = ecr.Repository.from_repository_name(
            self, id=f"ecr-{application_ecr_name}", repository_name=application_ecr_name
        )
        image_uri = f"{repo.repository_uri}:{APPLICATION_IMAGE_NAME}"
        ECRDeployment(
            self,
            "RoboticsImageUri",
            src=DockerImageName(local_image.image_uri),
            dest=DockerImageName(image_uri),
        )
        return image_uri

    def create_sqs(self, sqs_name: str, env: Environment) -> str:
        sqs.Queue(self, sqs_name, visibility_timeout=Duration.seconds(60))
        return f"https://sqs.{env.region}.amazonaws.com/{env.account}/{sqs_name}"

    def get_fsx_static_provisioning_manifest(
        self,
        volume_handle: str,
        mount_point: str,
        env: Environment,
    ) -> str:
        t = Template(open(os.path.join(project_dir, "manifests/fsx_static_provisioning.yaml"), "r").read())
        return t.substitute(
            VOLUME_HANDLE=volume_handle,
            MOUNT_NAME=mount_point,
            REGION=env.region,
        )
