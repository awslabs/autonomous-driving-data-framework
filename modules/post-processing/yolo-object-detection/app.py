# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

from aws_cdk import App, CfnOutput, Environment

from stack import ObjectDetection

project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


ecr_repository_arn = os.getenv(_param("ECR_REPOSITORY_ARN"))
full_access_policy = os.getenv(_param("FULL_ACCESS_POLICY_ARN"))

if not ecr_repository_arn:
    raise ValueError("ECR Repository ARN is missing.")

if not full_access_policy:
    raise ValueError("S3 Full Access Policy ARN is missing.")


def generate_description() -> str:
    soln_id = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_ID", None)
    soln_name = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_NAME", None)
    soln_version = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_VERSION", None)

    desc = "(SO9154) Autonomous Driving Data Framework (ADDF) - yolop-lane-det"
    if soln_id and soln_name and soln_version:
        desc = f"({soln_id}) {soln_name}. Version {soln_version}"
    elif soln_id and soln_name:
        desc = f"({soln_id}) {soln_name}"
    return desc


app = App()

stack = ObjectDetection(
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
    ecr_repository_arn=ecr_repository_arn,
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
