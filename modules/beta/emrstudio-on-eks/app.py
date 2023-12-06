# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# type: ignore

import json
import os

import aws_cdk
from aws_cdk import App

from rbac_stack import EmrEksRbacStack
from studio_stack import StudioLiveStack

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


vpc_id = os.getenv(_param("VPC_ID"))  # required
private_subnet_ids = json.loads(os.getenv(_param("PRIVATE_SUBNET_IDS")))  # required

if not vpc_id:
    raise ValueError("missing input parameter vpc-id")

if not private_subnet_ids:
    raise ValueError("missing input parameter private-subnet-ids")

eks_cluster_name = os.getenv(_param("EKS_CLUSTER_NAME"), "")  # required
eks_admin_role_arn = os.getenv(_param("EKS_CLUSTER_ADMIN_ROLE_ARN"), "")  # required
eks_oidc_arn = os.getenv(_param("EKS_OIDC_ARN"), "")  # required
eks_openid_issuer = os.getenv(_param("EKS_OPENID_ISSUER"), "")  # required
artifact_bucket_name = os.getenv(_param("ARTIFACT_BUCKET_NAME"))  # required
sso_username = os.getenv(_param("SSO_USERNAME"))  # required
emr_eks_namespace = os.getenv(_param("EMR_EKS_NAMESPACE"), "emr-studio")

app = App()

eks_stack = EmrEksRbacStack(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}-rbac",
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
    deployment=deployment_name,
    module=module_name,
    eks_cluster_name=eks_cluster_name,
    eks_admin_role_arn=eks_admin_role_arn,
    eks_oidc_arn=eks_oidc_arn,
    eks_openid_issuer=eks_openid_issuer,
    emr_namespace=emr_eks_namespace,
)

emr_studio = StudioLiveStack(
    app,
    id=f"addf-{deployment_name}-{module_name}",
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
    deployment=deployment_name,
    module=module_name,
    vpc_id=vpc_id,
    private_subnet_ids=private_subnet_ids,
    artifact_bucket_name=artifact_bucket_name,
    eks_cluster_name=eks_cluster_name,
    execution_role_arn=eks_stack.job_role.role_arn,
    emr_namespace=emr_eks_namespace,
    sso_username=sso_username,
)

app.synth(force=True)
