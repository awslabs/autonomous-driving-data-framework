# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

from aws_cdk import App, CfnOutput, Environment
from stack import TrainingDags

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")
eks_cluster_name = os.getenv("ADDF_PARAMETER_EKS_CLUSTER_NAME", "")
eks_admin_role_arn = os.getenv("ADDF_PARAMETER_EKS_CLUSTER_ADMIN_ROLE_ARN", "")
eks_oidc_provider_arn = os.getenv("ADDF_PARAMETER_EKS_OIDC_ARN", "")

app = App()

stack = TrainingDags(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    eks_cluster_name=eks_cluster_name,
    eks_admin_role_arn=eks_admin_role_arn,
    eks_openid_connect_provider_arn=eks_oidc_provider_arn,
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
        }
    ),
)

app.synth(force=True)
