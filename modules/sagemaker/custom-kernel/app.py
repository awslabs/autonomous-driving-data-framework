#!/usr/bin/env python3
import os

import aws_cdk as cdk
from aws_cdk import CfnOutput

from stack import CustomKernelStack

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")
app_prefix = f"addf-{deployment_name}-{module_name}"

DEFAULT_SAGEMAKER_IMAGE_NAME = f"{app_prefix}-sm-image"
DEFAULT_APP_IMAGE_CONFIG_NAME = f"addf-{deployment_name}-app-config"


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


sagemaker_image_name = os.getenv(
    _param("SAGEMAKER_IMAGE_NAME"), DEFAULT_SAGEMAKER_IMAGE_NAME
)
app_image_config_name = os.getenv(
    _param("APP_IMAGE_CONFIG_NAME"), DEFAULT_APP_IMAGE_CONFIG_NAME
)

environment = cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)

app = cdk.App()
stack = CustomKernelStack(
    app,
    app_prefix,
    app_prefix=app_prefix,
    env=environment,
)

CfnOutput(
    stack,
    "SageMakerCustomKernelRoleArn",
    value=stack.sagemaker_studio_image_role.role_arn,
)

app.synth()
