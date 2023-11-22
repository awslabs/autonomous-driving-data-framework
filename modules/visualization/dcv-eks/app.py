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

if len(f"{project_name}-{deployment_name}") > 36:
    raise ValueError("This module cannot support a project+deployment name character length greater than 35")


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


dcv_namespace = os.getenv(_param("DCV_NAMESPACE"))
dcv_node_port = os.getenv(_param("DCV_NODE_PORT"))
dcv_image_repo_uri = os.getenv(_param("DCV_IMAGE_REPO_URI"))
eks_cluster_admin_role_arn = os.getenv(_param("EKS_CLUSTER_ADMIN_ROLE_ARN"))
eks_cluster_name = os.getenv(_param("EKS_CLUSTER_NAME"))
eks_oidc_arn = os.getenv(_param("EKS_OIDC_ARN"))
eks_cluster_open_id_connect_issuer = os.getenv(_param("EKS_CLUSTER_OPEN_ID_CONNECT_ISSUER"))
eks_cluster_security_group_id = os.getenv(_param("EKS_CLUSTER_SECURITY_GROUP_ID"))
eks_node_role_arn = os.getenv(_param("EKS_NODE_ROLE_ARN"))


def generate_description() -> str:
    soln_id = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_ID", None)
    soln_name = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_NAME", None)
    soln_version = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_VERSION", None)

    desc = "My Module Default Description"
    if soln_id and soln_name and soln_version:
        desc = f"({soln_id}) {soln_name}. Version {soln_version}"
    elif soln_id and soln_name:
        desc = f"({soln_id}) {soln_name}"
    return desc


app = App()

dcv_eks_stack = DcvEksStack(
    scope=app,
    id=f"{project_name}-{deployment_name}-{module_name}",
    project_name=cast(str, project_name),
    deployment_name=cast(str, deployment_name),
    module_name=cast(str, module_name),
    stack_description=generate_description(),
    dcv_namespace=dcv_namespace,
    dcv_image_repo_uri=dcv_image_repo_uri,
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
            "temp": "test"
        }
    ),
)

app.synth()
