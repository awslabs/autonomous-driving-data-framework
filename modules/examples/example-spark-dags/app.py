# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

import aws_cdk
from aws_cdk import App, CfnOutput
from stack import DagIamRole

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")
mwaa_exec_role = os.getenv("ADDF_PARAMETER_MWAA_EXEC_ROLE_ARN", "")
raw_bucket_name = os.getenv("ADDF_PARAMETER_RAW_BUCKET_NAME", "")
app = App()

stack = DagIamRole(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    mwaa_exec_role=mwaa_exec_role,
    raw_bucket_name=raw_bucket_name,
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string({"DagRoleArn": stack.dag_role.role_arn}),
)

app.synth(force=True)
