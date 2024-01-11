# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from string import Template
from typing import Any, Optional, cast

import yaml
from aws_cdk import Environment, Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_eks as eks
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct

project_dir = os.path.dirname(os.path.abspath(__file__))

ADDF_DISPLAY_SOCKET_PATH = "/var/addf/dcv-eks/sockets"
ADDF_DEFAULT_DISPLAY_NUMER = ":0"
ADDF_SSM_PARAMETER_STORE_DISPLAY_NAME = "dcv-display"
ADDF_SSM_PARAMETER_STORE_MOUNT_PATH_NAME = "dcv-socket-mount-path"


class DcvEksStack(Stack):  # type: ignore
    def __init__(
        self,
        scope: Construct,
        id: str,
        project_name: str,
        deployment_name: str,
        module_name: str,
        dcv_namespace: str,
        dcv_image_uri: str,
        eks_cluster_name: str,
        eks_cluster_admin_role_arn: str,
        eks_oidc_arn: str,
        eks_cluster_open_id_connect_issuer: str,
        eks_cluster_security_group_id: str,
        eks_node_role_arn: str,
        dcv_node_port: str,
        env: Environment,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.project_name = project_name
        self.deployment_name = deployment_name
        self.module_name = module_name

        dep_mod = f"{self.project_name}-{self.deployment_name}-{self.module_name}"
        dep_mod = dep_mod[:64]
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=dep_mod)

        provider = eks.OpenIdConnectProvider.from_open_id_connect_provider_arn(
            self, f"{dep_mod}-provider", eks_oidc_arn
        )

        # create parameter store names
        parameter_store_prefix = f"/{self.project_name}/{self.deployment_name}/{self.module_name}"
        self.display_parameter_name = f"{parameter_store_prefix}/{ADDF_SSM_PARAMETER_STORE_DISPLAY_NAME}"
        self.socket_mount_path_parameter_name = f"{parameter_store_prefix}/{ADDF_SSM_PARAMETER_STORE_MOUNT_PATH_NAME}"
        self.add_ssm_parameter_store(self.display_parameter_name, self.socket_mount_path_parameter_name)

        self.update_node_role_permissions(eks_node_role_arn, env.region)
        self.eks_admin_role = self.add_eks_dcv_role(
            eks_cluster_open_id_connect_issuer, eks_oidc_arn, parameter_store_prefix, env
        )

        eks_cluster = eks.Cluster.from_cluster_attributes(
            self,
            f"{dep_mod}-eks-cluster",
            cluster_name=eks_cluster_name,
            kubectl_role_arn=eks_cluster_admin_role_arn,
            open_id_connect_provider=provider,
        )

        namespace_manifest = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": dcv_namespace,
            },
        }

        # Create the KubernetesManifest resource
        loop_iteration = 0
        manifest_id = "DCVAgent" + str(loop_iteration)
        k8s_namespace = eks_cluster.add_manifest(manifest_id, namespace_manifest)
        loop_iteration += 1

        t = Template(open(os.path.join(project_dir, "dcv-config/dcv-agent.yaml"), "r").read())
        dcv_agent_yaml_file = t.substitute(
            NAMESPACE=dcv_namespace,
            IMAGE=dcv_image_uri,
            REGION=env.region,
            SOCKET_PATH=ADDF_DISPLAY_SOCKET_PATH,
            DISPLAY_PARAMETER_NAME=self.display_parameter_name,
        )

        dcv_agent_yaml = yaml.load(dcv_agent_yaml_file, Loader=yaml.FullLoader)
        manifest_id = "DCVAgent" + str(loop_iteration)
        loop_iteration += 1
        dcv_agent_resource = eks_cluster.add_manifest(manifest_id, dcv_agent_yaml)

        t = Template(open(os.path.join(project_dir, "dcv-config/dcv-agent-setup.yaml"), "r").read())
        dcv_agent_yaml_file = t.substitute(
            NAMESPACE=dcv_namespace,
            NODEPORT=dcv_node_port,
            RUNTIME_ROLE_ARN=self.eks_admin_role.role_arn,
            SOCKET_PATH=ADDF_DISPLAY_SOCKET_PATH,
        )
        dcv_agent_yaml = list(yaml.load_all(dcv_agent_yaml_file, Loader=yaml.FullLoader))
        for value in dcv_agent_yaml:
            loop_iteration = loop_iteration + 1
            manifest_id = "DCVAgent" + str(loop_iteration)
            k8s_resource = eks_cluster.add_manifest(manifest_id, value)
            k8s_resource.node.add_dependency(k8s_namespace)
            dcv_agent_resource.node.add_dependency(k8s_resource)

        self.add_security_group_permissions(eks_cluster_security_group_id, dcv_node_port)

        NagSuppressions.add_stack_suppressions(
            self,
            apply_to_nested_stacks=True,
            suppressions=[
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-IAM4",
                        "reason": "Managed Policies are for src account roles only",
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

    def add_ssm_parameter_store(self, display_parameter_name: str, socket_mount_parameter_name: str) -> None:
        ssm.StringParameter(
            self,
            "display-parameter",
            description="DISPLAY environment variable for application pods",
            parameter_name=display_parameter_name,
            string_value=ADDF_DEFAULT_DISPLAY_NUMER,
        )
        ssm.StringParameter(
            self,
            "shared-dir-parameter",
            description="Shared directory for application access display socket",
            parameter_name=socket_mount_parameter_name,
            string_value=ADDF_DISPLAY_SOCKET_PATH,
        )

    def add_eks_dcv_role(
        self, eks_cluster_open_id_connect_issuer: str, eks_oidc_arn: str, ssm_parameter_prefix: str, env: Environment
    ) -> iam.Role:
        role = iam.Role(
            self,
            "Role",
            assumed_by=iam.FederatedPrincipal(
                eks_oidc_arn,
                {"StringLike": {f"{eks_cluster_open_id_connect_issuer}:sub": "system:serviceaccount:*"}},
                "sts:AssumeRoleWithWebIdentity",
            ),
        )

        role.add_to_principal_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
                resources=[f"arn:aws:secretsmanager:{env.region}:{env.account}:secret:dcv-cred-*"],
            )
        )

        role.add_to_principal_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["ssm:DescribeParameters", "ssm:PutParameter", "ssm:GetParameter"],
                resources=[f"arn:aws:ssm:{env.region}:{env.account}:parameter{ssm_parameter_prefix}/dcv-*"],
            )
        )
        return role

    def update_node_role_permissions(self, eks_node_role_arn: str, region: Optional[str]) -> None:
        node_role = iam.Role.from_role_arn(self, "NodeRole", eks_node_role_arn)
        node_role.add_to_principal_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                ],
                resources=[f"arn:aws:s3:::dcv-license.{region}/*"],
            )
        )

    def add_security_group_permissions(self, eks_cluster_security_group_id: str, dcv_node_port: str) -> None:
        security_group = ec2.SecurityGroup.from_security_group_id(
            self, "SG", eks_cluster_security_group_id, mutable=True
        )
        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(int(dcv_node_port)),
            "allow dcv NodePort from the everywhere around the world",
        )
        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.udp(int(dcv_node_port)),
            "allow dcv NodePort from the everywhere around the world",
        )
