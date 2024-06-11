# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

from aws_cdk import App, CfnOutput, Environment

from stack import LaneDetection

project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


full_access_policy = os.getenv(_param("FULL_ACCESS_POLICY_ARN"))

if not full_access_policy:
    raise ValueError("S3 Full Access Policy ARN is missing.")

app = App()

stack = LaneDetection(
    scope=app,
    id=f"{project_name}-{deployment_name}-{module_name}",
    project_name=project_name,
    deployment_name=deployment_name,
    module_name=module_name,
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
    s3_access_policy=full_access_policy,
)


CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "ImageUri": stack.image_uri,
            "EcrRepoName": stack.repository_name,
            "ExecutionRole": stack.role.role_arn,
        }
    ),
)

app.synth(force=True)
