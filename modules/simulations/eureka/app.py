# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from typing import cast

from aws_cdk import App, CfnOutput, Environment

from stack import EurekaStack

# Project specific
project_name = os.getenv("SEEDFARMER_PROJECT_NAME")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME")
module_name = os.getenv("SEEDFARMER_MODULE_NAME")

if len(f"{project_name}-{deployment_name}") > 36:
    raise ValueError(
        "This module cannot support a project+deployment name character length greater than 35"
    )


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


eks_cluster_admin_role_arn = os.getenv(_param("EKS_CLUSTER_ADMIN_ROLE_ARN"), "")
eks_cluster_name = os.getenv(_param("EKS_CLUSTER_NAME"), "")
eks_oidc_arn = os.getenv(_param("EKS_OIDC_ARN"), "")
eks_cluster_open_id_connect_issuer = os.getenv(
    _param("EKS_CLUSTER_OPEN_ID_CONNECT_ISSUER"), ""
)
application_ecr_name = os.getenv(_param("APPLICATION_ECR_NAME"), "")
sqs_name = os.getenv(_param("SQS_NAME"), "")
fsx_volume_handle = os.getenv(_param("FSX_VOLUME_HANDLE"), "")
fsx_mount_point = os.getenv(_param("FSX_MOUNT_POINT"), "")
data_bucket_name = os.getenv(_param("DATA_BUCKET_NAME"), "")


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

eureka_stack = EurekaStack(
    scope=app,
    id=f"{project_name}-{deployment_name}-{module_name}",
    project_name=cast(str, project_name),
    deployment_name=cast(str, deployment_name),
    module_name=cast(str, module_name),
    stack_description=generate_description(),
    eks_cluster_name=eks_cluster_name,
    eks_cluster_admin_role_arn=eks_cluster_admin_role_arn,
    eks_oidc_arn=eks_oidc_arn,
    eks_cluster_open_id_connect_issuer=eks_cluster_open_id_connect_issuer,
    simulation_data_bucket_name=data_bucket_name,
    sqs_name=sqs_name,
    fsx_volume_handle=fsx_volume_handle,
    fsx_mount_point=fsx_mount_point,
    application_ecr_name=application_ecr_name,
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)


CfnOutput(
    scope=eureka_stack,
    id="metadata",
    value=eureka_stack.to_json_string(
        {
            "IamRoleArn": eureka_stack.iam_role_arn,
            "ApplicationImageUri": eureka_stack.application_image_uri,
            "SqsUrl": eureka_stack.sqs_url,
        }
    ),
)

app.synth()
