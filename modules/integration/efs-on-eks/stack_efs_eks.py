# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from typing import Any, cast

import cdk_nag
from aws_cdk import Aspects, Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_eks as eks
from aws_cdk.lambda_layer_kubectl_v29 import KubectlV29Layer
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct

project_dir = os.path.dirname(os.path.abspath(__file__))


class EFSFileStorageOnEKS(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        deployment_name: str,
        module_name: str,
        efs_file_system_id: str,
        efs_security_group_id: str,
        eks_cluster_name: str,
        eks_admin_role_arn: str,
        eks_oidc_arn: str,
        eks_cluster_security_group_id: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            scope,
            id,
            description="This stack connects an existing EFS to an existing EKS",
            **kwargs,
        )

        self.deployment_name = deployment_name
        self.module_name = module_name
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{self.deployment_name}")

        dep_mod = f"addf-{self.deployment_name}-{self.module_name}"
        dep_mod = dep_mod[:30]

        # Import EKS Cluster
        provider = eks.OpenIdConnectProvider.from_open_id_connect_provider_arn(
            self, f"{dep_mod}-provider", eks_oidc_arn
        )
        eks_cluster = eks.Cluster.from_cluster_attributes(
            self,
            f"{dep_mod}-eks-cluster",
            cluster_name=eks_cluster_name,
            kubectl_role_arn=eks_admin_role_arn,
            open_id_connect_provider=provider,
            kubectl_layer=KubectlV29Layer(self, "Kubectlv29Layer"),
        )

        efs_security_group = ec2.SecurityGroup.from_security_group_id(self, "EKSSecurityGroup", efs_security_group_id)
        eks_security_group = ec2.SecurityGroup.from_security_group_id(
            self, "EFSSecurityGroup", eks_cluster_security_group_id
        )
        efs_security_group.connections.allow_from(
            eks_security_group,
            ec2.Port.tcp(2049),
            "allowtraffic from EKS nodes over port 2049",
        )

        # Set up the StorageClass pointing at the new CSI Driver
        # https://github.com/kubernetes-sigs/aws-efs-csi-driver/blob/master/examples/kubernetes/dynamic_provisioning/specs/storageclass.yaml
        self.storage_class_name = f"{module_name}-efs"
        eks_cluster.add_manifest(
            "EFSCSIStorageClass",
            {
                "kind": "StorageClass",
                "apiVersion": "storage.k8s.io/v1",
                "metadata": {"name": self.storage_class_name},
                "provisioner": "efs.csi.aws.com",
                "parameters": {
                    "provisioningMode": "efs-ap",
                    "fileSystemId": efs_file_system_id,
                    "directoryPerms": "700",
                    "gidRangeStart": "1000",
                    "gidRangeEnd": "2000",
                    "basePath": "/dynamic_provisioning",
                },
            },
        )

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
                        "reason": "Resource access restriced to ADDF resources",
                    }
                ),
            ],
        )
