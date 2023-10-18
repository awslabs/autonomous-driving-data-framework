# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

from aws_cdk import App, CfnOutput, Environment, RemovalPolicy

from stack import ObjectDetection

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


full_access_policy = os.getenv(_param("FULL_ACCESS_POLICY_ARN"))
removal_policy = os.getenv(_param("REMOVAL_POLICY"), "")

if not full_access_policy:
    raise ValueError("S3 Full Access Policy ARN is missing.")


def generate_description() -> str:
    soln_id = os.getenv("ADDF_PARAMETER_SOLUTION_ID", None)
    soln_name = os.getenv("ADDF_PARAMETER_SOLUTION_NAME", None)
    soln_version = os.getenv("ADDF_PARAMETER_SOLUTION_VERSION", None)

    desc = "(SO9154) Autonomous Driving Data Framework (ADDF) - yolop-lane-det"
    if soln_id and soln_name and soln_version:
        desc = f"({soln_id}) {soln_name}. Version {soln_version}"
    elif soln_id and soln_name:
        desc = f"({soln_id}) {soln_name}"
    return desc


app = App()

stack = ObjectDetection(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
    s3_access_policy=full_access_policy,
    removal_policy=RemovalPolicy.RETAIN if removal_policy.upper() == "RETAIN" else RemovalPolicy.DESTROY,
    stack_description=generate_description(),
)


base_image = (
    f"763104351884.dkr.ecr.{stack.region}.amazonaws.com/pytorch-inference:1.12.1-gpu-py38-cu113-ubuntu20.04-sagemaker"
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "ImageUri": stack.image_uri,
            "EcrRepoName": stack.repository_name,
            "ExecutionRole": stack.role.role_arn,
            "BaseImage": base_image,
        }
    ),
)

app.synth(force=True)
