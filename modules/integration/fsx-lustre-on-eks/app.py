# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from typing import cast

import aws_cdk
from aws_cdk import App, CfnOutput

from stack_fsx_eks import FSXFileStorageOnEKS

project_name = os.getenv("AWS_CODESEEDER_NAME", "addf")


def _proj(name: str) -> str:
    return f"{project_name.upper()}_{name}"


def _param(name: str) -> str:
    return f"{project_name.upper()}_PARAMETER_{name}"


deployment_name = os.getenv(_proj("DEPLOYMENT_NAME"))
module_name = os.getenv(_proj("MODULE_NAME"))

eks_cluster_name = os.getenv(_param("EKS_CLUSTER_NAME"))
eks_admin_role_arn = os.getenv(_param("EKS_CLUSTER_ADMIN_ROLE_ARN"))
eks_oidc_arn = os.getenv(_param("EKS_OIDC_ARN"))
eks_cluster_sg_id = os.getenv(_param("EKS_CLUSTER_SECURITY_GROUP_ID"))

fsx_file_system_id = os.getenv(_param("FSX_FILE_SYSTEM_ID"))
fsx_security_group_id = os.getenv(_param("FSX_SECURITY_GROUP_ID"))
fsx_mount_name = os.getenv(_param("FSX_MOUNT_NAME"))
fsx_dns_name = os.getenv(_param("FSX_DNS_NAME"))

# This gets set in the deployspec...NOTE no PARAMETER prefix
eks_namespace = os.getenv("EKS_NAMESPACE")

if not eks_namespace:
    print("No EKS Namespace defined...error")
    exit(1)


app = App()


stack = FSXFileStorageOnEKS(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=cast(str, deployment_name),
    module_name=cast(str, module_name),
    fsx_file_system_id=cast(str, fsx_file_system_id),
    fsx_security_group_id=cast(str, fsx_security_group_id),
    fsx_mount_name=cast(str, fsx_mount_name),
    fsx_dns_name=cast(str, fsx_dns_name),
    eks_cluster_name=cast(str, eks_cluster_name),
    eks_admin_role_arn=cast(str, eks_admin_role_arn),
    eks_oidc_arn=cast(str, eks_oidc_arn),
    eks_cluster_security_group_id=cast(str, eks_cluster_sg_id),
    eks_namespace=eks_namespace,
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)
CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "StorageClassName": stack.storage_class_name,
            "PersistentVolumeName": stack.pv_name,
            "PersistentVolumeClaimName": stack.pvc_name,
            "Namespace": eks_namespace,
        }
    ),
)


app.synth(force=True)
