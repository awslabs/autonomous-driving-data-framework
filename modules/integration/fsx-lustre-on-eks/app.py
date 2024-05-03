# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from typing import cast

import aws_cdk
from aws_cdk import App, CfnOutput

from stack_fsx_eks import FSXFileStorageOnEKS


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")

eks_cluster_name = os.getenv(_param("EKS_CLUSTER_NAME"))
eks_admin_role_arn = os.getenv(_param("EKS_CLUSTER_ADMIN_ROLE_ARN"))
eks_oidc_arn = os.getenv(_param("EKS_OIDC_ARN"))
eks_cluster_sg_id = os.getenv(_param("EKS_CLUSTER_SECURITY_GROUP_ID"))

fsx_file_system_id = os.getenv(_param("FSX_FILE_SYSTEM_ID"))
fsx_security_group_id = os.getenv(_param("FSX_SECURITY_GROUP_ID"))
fsx_mount_name = os.getenv(_param("FSX_MOUNT_NAME"))
fsx_dns_name = os.getenv(_param("FSX_DNS_NAME"))

fsx_storage_capacity = int(os.getenv(_param("FSX_STORAGE_CAPACITY"), 1200))

# This gets set in the deployspec...NOTE no PARAMETER prefix
eks_namespace = os.getenv("EKS_NAMESPACE")

if not eks_namespace:
    raise ValueError("No EKS Namespace defined...error")


if fsx_storage_capacity not in [1200, 2400] and (fsx_storage_capacity % 3600) != 0:
    raise ValueError("Storage_capacity must be 1200, 2400 or an increment of 3600 - see README")

app = App()


stack = FSXFileStorageOnEKS(
    scope=app,
    id=f"{project_name}-{deployment_name}-{module_name}",
    project_name=project_name,
    deployment_name=deployment_name,
    module_name=module_name,
    fsx_file_system_id=cast(str, fsx_file_system_id),
    fsx_security_group_id=cast(str, fsx_security_group_id),
    fsx_mount_name=cast(str, fsx_mount_name),
    fsx_dns_name=cast(str, fsx_dns_name),
    fsx_storage_capacity=f"{fsx_storage_capacity}Gi",
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
