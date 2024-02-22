# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from typing import cast

from aws_cdk import App, CfnOutput, Environment

from stack import DcvEksStack

# Project specific
project_name = os.getenv("SEEDFARMER_PROJECT_NAME")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME")
module_name = os.getenv("SEEDFARMER_MODULE_NAME")
DEFAULT_DCV_NAMESPACE = "dcv"
DEFAULT_DCV_NODEPORT = "31980"


if len(f"{project_name}-{deployment_name}") > 36:
    raise ValueError("This module cannot support a project+deployment name character length greater than 35")


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


dcv_namespace = os.getenv(_param("DCV_NAMESPACE"), DEFAULT_DCV_NAMESPACE)
dcv_node_port = os.getenv(_param("DCV_NODEPORT"), DEFAULT_DCV_NODEPORT)
dcv_image_uri = os.getenv(_param("DCV_IMAGE_URI"), "")
eks_cluster_admin_role_arn = os.getenv(_param("EKS_CLUSTER_ADMIN_ROLE_ARN"), "")
eks_cluster_name = os.getenv(_param("EKS_CLUSTER_NAME"), "")
eks_oidc_arn = os.getenv(_param("EKS_OIDC_ARN"), "")
eks_cluster_open_id_connect_issuer = os.getenv(_param("EKS_CLUSTER_OPEN_ID_CONNECT_ISSUER"), "")
eks_cluster_security_group_id = os.getenv(_param("EKS_CLUSTER_SECURITY_GROUP_ID"), "")
eks_node_role_arn = os.getenv(_param("EKS_NODE_ROLE_ARN"), "")

app = App()
for name, value in os.environ.items():
    print("{0}: {1}".format(name, value))
dcv_eks_stack = DcvEksStack(
    scope=app,
    id=f"{project_name}-{deployment_name}-{module_name}",
    project_name=cast(str, project_name),
    deployment_name=cast(str, deployment_name),
    module_name=cast(str, module_name),
    dcv_namespace=dcv_namespace,
    dcv_image_uri=dcv_image_uri,
    eks_cluster_name=eks_cluster_name,
    eks_cluster_admin_role_arn=eks_cluster_admin_role_arn,
    eks_oidc_arn=eks_oidc_arn,
    eks_cluster_open_id_connect_issuer=eks_cluster_open_id_connect_issuer,
    eks_cluster_security_group_id=eks_cluster_security_group_id,
    eks_node_role_arn=eks_node_role_arn,
    dcv_node_port=dcv_node_port,
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)


CfnOutput(
    scope=dcv_eks_stack,
    id="metadata",
    value=dcv_eks_stack.to_json_string(
        {
            "DcvEksRoleArn": dcv_eks_stack.eks_admin_role.role_arn,
            "DcvNamespace": dcv_namespace,
            "DcvNodeport": dcv_node_port,
            "DcvDisplayParameterName": dcv_eks_stack.display_parameter_name,
            "DcvSocketMountPathParameterName": dcv_eks_stack.socket_mount_path_parameter_name,
        }
    ),
)

app.synth()
