# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from typing import cast

import aws_cdk
from aws_cdk import App, CfnOutput

from stack_efs_eks import EFSFileStorageOnEKS

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

efs_file_system_id = os.getenv(_param("EFS_FILE_SYSTEM_ID"))
efs_security_group_id = os.getenv(_param("EFS_SECURITY_GROUP_ID"))


app = App()

efs_stack = EFSFileStorageOnEKS(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=cast(str, deployment_name),
    module_name=cast(str, module_name),
    efs_file_system_id=cast(str, efs_file_system_id),
    efs_security_group_id=cast(str, efs_security_group_id),
    eks_cluster_name=cast(str, eks_cluster_name),
    eks_admin_role_arn=cast(str, eks_admin_role_arn),
    eks_oidc_arn=cast(str, eks_oidc_arn),
    eks_cluster_security_group_id=cast(str, eks_cluster_sg_id),
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)
CfnOutput(
    scope=efs_stack,
    id="metadata",
    value=efs_stack.to_json_string(
        {
            "EFSStorageClassName": efs_stack.storage_class_name,
            "EKSClusterName": eks_cluster_name,
        }
    ),
)


app.synth(force=True)
