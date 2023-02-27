import json
import os
from typing import cast

import aws_cdk
from aws_cdk import CfnOutput

from stack import SagemakerStudioStack

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")
app_prefix = f"addf-{deployment_name}-{module_name}"

DEFAULT_STUDIO_DOMAIN_NAME = f"{app_prefix}-studio-domain"
DEFAULT_STUDIO_BUCKET_NAME = f"{app_prefix}-bucket"
DEFAULT_CUSTOM_KERNEL_APP_CONFIG_NAME = None
DEFAULT_CUSTOM_KERNEL_IMAGE_NAME = None


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


vpc_id = os.getenv(_param("VPC_ID"))
subnet_ids = json.loads(os.getenv(_param("SUBNET_IDS"), "[]"))
studio_domain_name = os.getenv(_param("STUDIO_DOMAIN_NAME"), DEFAULT_STUDIO_DOMAIN_NAME)
studio_bucket_name = os.getenv(_param("STUDIO_BUCKET_NAME"), DEFAULT_STUDIO_BUCKET_NAME)
app_image_config_name = os.getenv(
    _param("CUSTOM_KERNEL_APP_CONFIG_NAME"), DEFAULT_CUSTOM_KERNEL_APP_CONFIG_NAME
)
image_name = os.getenv(
    _param("CUSTOM_KERNEL_IMAGE_NAME"), DEFAULT_CUSTOM_KERNEL_IMAGE_NAME
)

environment = aws_cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)

data_science_users = json.loads(os.getenv(_param("DATA_SCIENCE_USERS"), "[]"))
lead_data_science_users = json.loads(os.getenv(_param("LEAD_DATA_SCIENCE_USERS"), "[]"))

app = aws_cdk.App()
stack = SagemakerStudioStack(
    app,
    f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    vpc_id=cast(str, vpc_id),
    subnet_ids=subnet_ids,
    studio_domain_name=studio_domain_name,
    studio_bucket_name=studio_bucket_name,
    data_science_users=data_science_users,
    lead_data_science_users=lead_data_science_users,
    env=environment,
    app_image_config_name=cast(str, app_image_config_name),
    image_name=cast(str, image_name),
)

CfnOutput(
    stack,
    "LeadDataScientistRoleArn",
    value=stack.sm_roles.lead_data_scientist_role.role_arn,
)
CfnOutput(
    stack,
    "DataScientistRoleArn",
    value=stack.sm_roles.data_scientist_role.role_arn,
)
CfnOutput(
    stack,
    "StudioDomainName",
    value=stack.studio_domain.domain_name,
)
CfnOutput(
    stack,
    "StudioDomainId",
    value=stack.studio_domain.attr_domain_id,
)
CfnOutput(stack, "StudioBucketName", value=studio_bucket_name)
app.synth()
