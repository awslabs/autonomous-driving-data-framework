#!/usr/bin/env python3
import os

import aws_cdk as cdk
from ecr.ecr_stack import EcrStack

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")
app_prefix = f"addf-{deployment_name}-{module_name}"

DEFAULT_REPOSITORY_NAME = f"addf-{module_name}-ecr-repository"
DEFAULT_IMAGE_MUTABILITY = "IMMUTABLE"
DEFAULT_LIFECYCLE = None  # No lifecycle policy


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


environment = cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ["CDK_DEFAULT_REGION"],
)

repository_name = os.getenv(_param("REPOSITORY_NAME"), DEFAULT_REPOSITORY_NAME)
image_tag_mutability = os.getenv(_param("IMAGE_TAG_MUTABILITY"), DEFAULT_IMAGE_MUTABILITY)
lifecycle_max_image_count = os.getenv(_param("LIFECYCLE_MAX_IMAGE_COUNT"), DEFAULT_LIFECYCLE)
lifecycle_max_days = os.getenv(_param("LIFECYCLE_MAX_DAYS"), DEFAULT_LIFECYCLE)

app = cdk.App()
EcrStack(
    app,
    app_prefix,
    repository_name=repository_name,
    image_tag_mutability=image_tag_mutability,
    lifecycle_max_image_count=lifecycle_max_image_count,
    lifecycle_max_days=lifecycle_max_days,
    env=environment,
)

app.synth()
