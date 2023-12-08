# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os

import aws_cdk
from aws_cdk import App, CfnOutput

from stack import Eks

# Project specific
project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")

if len(f"{project_name}-{deployment_name}") > 36:
    raise ValueError("This module cannot support a project+deployment name character length greater than 35")
def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


# App specific
vpc_id = os.getenv(_param("VPC_ID"))  # required
dataplane_subnet_ids = json.loads(os.getenv(_param("DATAPLANE_SUBNET_IDS"), ""))  # required
controlplane_subnet_ids = json.loads(os.getenv(_param("CONTROLPLANE_SUBNET_IDS"), ""))  # required
custom_subnet_ids = (
    json.loads(os.getenv(_param("CUSTOM_SUBNET_IDS"))) if os.getenv(_param("CUSTOM_SUBNET_IDS")) else None
)
eks_version = os.getenv(_param("EKS_VERSION"))  # required
eks_compute_config = json.loads(os.getenv(_param("EKS_COMPUTE")))  # required
eks_addons_config = json.loads(os.getenv(_param("EKS_ADDONS")))  # required

if not vpc_id:
    raise ValueError("missing input parameter vpc-id")

if not dataplane_subnet_ids:
    raise ValueError("missing input parameter dataplane-subnet-ids")

if not controlplane_subnet_ids:
    raise ValueError("missing input parameter controlplane-subnet-ids")

if not eks_compute_config:
    raise ValueError("EKS Compute Configuration is missing")

if not eks_addons_config:
    raise ValueError("EKS Addons Configuration is missing")

app = App()

stack = Eks(
    scope=app,
    id=f"{project_name}-{deployment_name}-{module_name}",
    project_name=project_name,
    deployment_name=deployment_name,
    module_name=module_name,
    vpc_id=vpc_id,
    controlplane_subnet_ids=controlplane_subnet_ids,
    dataplane_subnet_ids=dataplane_subnet_ids,
    eks_version=eks_version,
    eks_compute_config=eks_compute_config,
    eks_addons_config=eks_addons_config,
    custom_subnet_ids=custom_subnet_ids,
    codebuild_sg_id=json.loads(os.getenv(_param("CODEBUILD_SG_ID")))[0]
    if os.getenv(_param("CODEBUILD_SG_ID"))
    else None,
    replicated_ecr_images_metadata=json.loads(os.getenv(_param("REPLICATED_ECR_IMAGES_METADATA")))
    if os.getenv(_param("REPLICATED_ECR_IMAGES_METADATA"))
    else {},
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
            "EksClusterName": stack.eks_cluster.cluster_name,
            # Cluster Creator role automatically gets added to RBAC system:masters group
            "EksClusterAdminRoleArn": stack.eks_cluster.admin_role.role_arn,
            "EksClusterSecurityGroupId": stack.eks_cluster.cluster_security_group.security_group_id,
            "EksOidcArn": stack.eks_cluster.open_id_connect_provider.open_id_connect_provider_arn,
            "EksClusterOpenIdConnectIssuer": stack.eks_cluster.cluster_open_id_connect_issuer,
            "CNIMetricsHelperRoleName": stack.cni_metrics_role_name,
            # Cluster Master role created as a part of this stack gets added to RBAC system:masters group
            "EksClusterMasterRoleArn": stack.eks_cluster_masterrole.role_arn,
        }
    ),
)

app.synth(force=True)
