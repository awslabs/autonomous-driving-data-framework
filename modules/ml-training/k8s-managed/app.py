# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os
from typing import cast

from aws_cdk import App, CfnOutput, Environment

from stack import TrainingPipeline

# Project specific
deployment_name = os.environ["ADDF_DEPLOYMENT_NAME"]
module_name = os.environ["ADDF_MODULE_NAME"]


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


eks_cluster_name = os.getenv(_param("EKS_CLUSTER_NAME"))
eks_admin_role_arn = os.getenv(_param("EKS_CLUSTER_ADMIN_ROLE_ARN"))
eks_oidc_provider_arn = os.getenv(_param("EKS_OIDC_ARN"))
eks_cluster_endpoint = os.getenv(_param("EKS_CLUSTER_ENDPOINT"))
eks_cert_auth_data = os.getenv(_param("EKS_CERT_AUTH_DATA"))
training_namespace_name = os.getenv(_param("TRAINING_NAMESPACE_NAME"))
training_image_uri = os.getenv(_param("TRAINING_IMAGE_URI"))

app = App()

stack = TrainingPipeline(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    eks_cluster_name=cast(str, eks_cluster_name),
    eks_admin_role_arn=cast(str, eks_admin_role_arn),
    eks_openid_connect_provider_arn=cast(str, eks_oidc_provider_arn),
    eks_cluster_endpoint=cast(str, eks_cluster_endpoint),
    eks_cert_auth_data=cast(str, eks_cert_auth_data),
    training_namespace_name=cast(str, training_namespace_name),
    training_image_uri=cast(str, training_image_uri),
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "EksServiceAccountRoleArn": stack.eks_service_account_role.role_arn,
            "TrainingNamespaceName": training_namespace_name,
        }
    ),
)
app.synth(force=True)
