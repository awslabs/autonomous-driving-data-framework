# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os
from typing import cast

import aws_cdk
from aws_cdk import App, CfnOutput
from stack import KubeflowUsersStack

project_name = os.getenv("AWS_CODESEEDER_NAME", "")
account_id = os.getenv("AWS_ACCOUNT_ID")


def _proj(name: str) -> str:
    return f"{project_name.upper()}_{name}"


def _param(name: str) -> str:
    return f"{project_name.upper()}_PARAMETER_{name}"


deployment_name = os.getenv(_proj("DEPLOYMENT_NAME"))
module_name = os.getenv(_proj("MODULE_NAME"))
eks_cluster_name = os.getenv(_param("EKS_CLUSTER_NAME"))  # required
eks_oidc_arn = os.getenv(_param("EKS_OIDC_ARN"))  # required
eks_openid_connect_issuer = os.getenv(_param("EKS_CLUSTER_OPEN_ID_CONNECT_ISSUER"))
users = os.getenv(_param("KUBEFLOW_USERS"))  # type: ignore
if not users:
    print("No Kubeflow Users Configured, exiting")
    exit(1)

app = App()

kf_users_stack = KubeflowUsersStack(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=cast(str, deployment_name),
    module_name=cast(str, module_name),
    eks_oidc_arn=cast(str, eks_oidc_arn),
    eks_openid_connect_issuer=cast(str, eks_openid_connect_issuer),
    users=json.loads(users),
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)

CfnOutput(
    scope=kf_users_stack,
    id="metadata",
    value=kf_users_stack.to_json_string({"KubeflowUsers": kf_users_stack.kf_users, "EksClusterName": eks_cluster_name}),
)

app.synth(force=True)
