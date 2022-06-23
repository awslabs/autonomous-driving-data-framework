import os

import aws_cdk
from aws_cdk import App

from stack import EksOpenSearchIntegrationStack

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


opensearch_sg_id = os.getenv(_param("OPENSEARCH_SG_ID"), "")
opensearch_domain_endpoint = os.getenv(_param("OPENSEARCH_DOMAIN_ENDPOINT"), "")
eks_cluster_name = os.getenv(_param("EKS_CLUSTER_NAME"), "")
eks_admin_role_arn = os.getenv(_param("EKS_CLUSTER_ADMIN_ROLE_ARN"), "")
eks_cluster_sg_id = os.getenv(_param("EKS_CLUSTER_SG_ID"), "")
eks_oidc_arn = os.getenv(_param("EKS_OIDC_ARN"), "")

app = App()

stack = EksOpenSearchIntegrationStack(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
    deployment=deployment_name,
    module=module_name,
    opensearch_sg_id=opensearch_sg_id,
    opensearch_domain_endpoint=opensearch_domain_endpoint,
    eks_cluster_name=eks_cluster_name,
    eks_admin_role_arn=eks_admin_role_arn,
    eks_cluster_sg_id=eks_cluster_sg_id,
    eks_oidc_arn=eks_oidc_arn,
)


app.synth(force=True)
