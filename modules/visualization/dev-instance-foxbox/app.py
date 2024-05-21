# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# type: ignore
""" Seedfarmer Module for Data Service Dev Instances """
import json
import os

from aws_cdk import App, CfnOutput, Environment
from stack import DataServiceDevInstancesStack

###################
# General Environment Variables
DEPLOYMENT_NAME = os.getenv("ADDF_DEPLOYMENT_NAME", None)
MODULE_NAME = os.getenv("ADDF_MODULE_NAME", None)
VPC_ID = os.getenv("ADDF_PARAMETER_VPC_ID", None)
INSTANCE_TYPE = os.getenv("ADDF_PARAMETER_INSTANCE_TYPE", "g4dn.xlarge")
INSTANCE_COUNT = int(os.getenv("ADDF_PARAMETER_INSTANCE_COUNT", "1"))
AMI_ID = os.getenv("ADDF_PARAMETER_AMI_ID", None)
S3_BUCKET_DATASET = os.getenv("ADDF_PARAMETER_S3_BUCKET_DATASET", None)
S3_BUCKET_SCRIPTS = os.getenv("ADDF_PARAMETER_S3_BUCKET_SCRIPTS", None)
DEMO_PASSWORD = os.getenv("ADDF_PARAMETER_DEMO_PASSWORD", None)

STACK_ID = "data-src-dev-instances"
if DEPLOYMENT_NAME and MODULE_NAME:
    STACK_ID = f"addf-{DEPLOYMENT_NAME}-{MODULE_NAME}"

ENV = Environment(
    account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
    region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
)

###################
# Stack
app = App()
stack = DataServiceDevInstancesStack(
    app,
    STACK_ID,
    env=ENV,
    deployment_name=DEPLOYMENT_NAME,
    module_name=MODULE_NAME,
    vpc_id=VPC_ID,
    instance_count=INSTANCE_COUNT,
    instance_type=INSTANCE_TYPE,
    ami_id=AMI_ID,
    demo_password=DEMO_PASSWORD,
    s3_bucket_dataset=S3_BUCKET_DATASET,
    s3_bucket_scripts=S3_BUCKET_SCRIPTS,
)

CfnOutput(scope=stack, id="metadata", value=json.dumps(stack.output_instances))

app.synth(force=True)
