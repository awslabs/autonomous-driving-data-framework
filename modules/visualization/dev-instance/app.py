# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# type: ignore

import json
import os

from aws_cdk import App, CfnOutput, Environment

from stack import DataServiceDevInstancesStack

# Project vars
project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


vpc_id = os.getenv(_param("VPC_ID"))
instance_type = os.getenv(_param("INSTANCE_TYPE"), "g4dn.xlarge")
instance_count = int(os.getenv(_param("INSTANCE_COUNT"), "1"))

ami_id = os.getenv(_param("AMI_ID"), None)
s3_dataset_bucket = os.getenv(_param("S3_DATASET_BUCKET"), None)
s3_script_bucket = os.getenv(_param("S3_SCRIPT_BUCKET"), None)

demo_password = os.getenv(_param("DEMO_PASSWORD"), None)

stack_id = "data-src-dev-instances"
if deployment_name and module_name:
    stack_id = f"{project_name}-{deployment_name}-{module_name}"

app = App()

env = Environment(
    account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
    region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
)

stack = DataServiceDevInstancesStack(
    scope=app,
    id=stack_id,
    env=env,
    project_name=project_name,
    deployment_name=deployment_name,
    module_name=module_name,
    vpc_id=vpc_id,
    instance_count=instance_count,
    instance_type=instance_type,
    ami_id=ami_id,
    demo_password=demo_password,
    s3_dataset_bucket=s3_dataset_bucket,
    s3_script_bucket=s3_script_bucket,
)


CfnOutput(scope=stack, id="metadata", value=json.dumps(stack.output_instances))

app.synth(force=True)
