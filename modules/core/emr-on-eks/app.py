# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# type: ignore

import os

import aws_cdk
from aws_cdk import App, CfnOutput

from airflow_emr_eks import AirflowEmrEksStack
from rbac_stack import EmronEksRbacStack

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


mwaa_exec_role = os.getenv(_param("MWAA_EXEC_ROLE"), "")
eks_cluster_name = os.getenv(_param("EKS_CLUSTER_NAME"), "")  # required
eks_admin_role_arn = os.getenv(_param("EKS_CLUSTER_ADMIN_ROLE_ARN"), "")  # required
eks_oidc_arn = os.getenv(_param("EKS_OIDC_ARN"), "")  # required
eks_openid_issuer = os.getenv(_param("EKS_OPENID_ISSUER"), "")  # required
artifact_bucket_name = os.getenv(_param("ARTIFACT_BUCKET_NAME"))  # required
emr_eks_namespace = os.getenv(_param("AIRFLOW_EMR_EKS_NAMESPACE"))  # required
raw_bucket_name = os.getenv(_param("RAW_BUCKET_NAME"))
logs_bucket_name = os.getenv(_param("LOGS_BUCKET_NAME"), "")

app = App()

eks_rbac_stack = EmronEksRbacStack(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}-rbac",
    deployment_name=deployment_name,
    module_name=module_name,
    mwaa_exec_role=mwaa_exec_role,
    eks_cluster_name=eks_cluster_name,
    eks_admin_role_arn=eks_admin_role_arn,
    eks_oidc_arn=eks_oidc_arn,
    eks_openid_issuer=eks_openid_issuer,
    emr_namespace=emr_eks_namespace,
    raw_bucket_name=raw_bucket_name,
    logs_bucket_name=logs_bucket_name,
    artifact_bucket_name=artifact_bucket_name,
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)

emr_eks_airflow = AirflowEmrEksStack(
    app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    mwaa_exec_role=mwaa_exec_role,
    eks_cluster_name=eks_cluster_name,
    emr_namespace=emr_eks_namespace,
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)

CfnOutput(
    scope=eks_rbac_stack,
    id="metadata",
    value=eks_rbac_stack.to_json_string(
        {
            "EmrJobExecutionRoleArn": eks_rbac_stack.job_role.role_arn,
        }
    ),
)

CfnOutput(
    scope=emr_eks_airflow,
    id="metadata",
    value=emr_eks_airflow.to_json_string(
        {
            "VirtualClusterId": emr_eks_airflow.emr_vc.attr_id,
        }
    ),
)


app.synth(force=True)
