import json
import os

import aws_cdk
from aws_cdk import App, CfnOutput

from stack import Eks

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME")
module_name = os.getenv("ADDF_MODULE_NAME")
vpc_id = os.getenv("ADDF_PARAMETER_VPC_ID")  # required
private_subnet_ids = json.loads(os.getenv("ADDF_PARAMETER_PRIVATE_SUBNET_IDS"))  # required
custom_subnet_ids = json.loads(os.getenv("ADDF_PARAMETER_CUSTOM_SUBNET_IDS"))
eks_version = os.getenv("ADDF_PARAMETER_EKS_VERSION")  # required
eks_compute_config = json.loads(os.getenv("ADDF_PARAMETER_EKS_COMPUTE"))  # required
eks_addons_config = json.loads(os.getenv("ADDF_PARAMETER_EKS_ADDONS"))  # required
if os.getenv("ADDF_PARAMETER_CODEBUILD_SG_ID"):
    codebuild_sg_id = json.loads(os.getenv("ADDF_PARAMETER_CODEBUILD_SG_ID"))[0]

if not vpc_id:
    raise Exception("missing input parameter vpc-id")

if not private_subnet_ids:
    raise Exception("missing input parameter private-subnet-ids")

if not eks_compute_config:
    raise ValueError("EKS Compute Configuration is missing.")

if not eks_addons_config:
    raise ValueError("EKS Addons Configuration is missing.")

app = App()

config = {
    "deployment_name": deployment_name,
    "module_name": module_name,
    "vpc_id": vpc_id,
    "private_subnet_ids": private_subnet_ids,
    "eks_version": eks_version,
    "eks_compute_config": eks_compute_config,
    "eks_addons_config": eks_addons_config,
    "custom_subnet_ids": custom_subnet_ids,
    "codebuild_sg_id": codebuild_sg_id if os.getenv("ADDF_PARAMETER_CODEBUILD_SG_ID") else None,
}

print(f"{module_name}")
stack = Eks(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    config=config,
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
            "EksClusterAdminRoleArn": stack.eks_cluster.admin_role.role_arn,
            "EksClusterKubectlRoleArn": stack.eks_cluster.kubectl_role.role_arn,
            "EksClusterSecurityGroupId": stack.eks_cluster.cluster_security_group.security_group_id,
            "EksOidcArn": stack.eks_cluster.open_id_connect_provider.open_id_connect_provider_arn,
            "EksClusterOpenIdConnectIssuer": stack.eks_cluster.cluster_open_id_connect_issuer,
            "CNIMetricsHelperRoleName": stack.cni_metrics_role_name,
            "EksClusterMasterRoleArn": stack.eks_cluster_masterrole.role_arn,
        }
    ),
)

app.synth(force=True)
