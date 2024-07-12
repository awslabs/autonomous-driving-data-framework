# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

from aws_cdk import App, CfnOutput, Environment

from stack import RosToPngBatchJob

project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


ecr_repository_arn = os.getenv(_param("ECR_REPOSITORY_ARN"))
full_access_policy = os.getenv(_param("FULL_ACCESS_POLICY_ARN"))
retries = int(os.getenv(_param("RETRIES"), 1))
timeout_seconds = int(os.getenv(_param("TIMEOUT_SECONDS"), 60))
vcpus = int(os.getenv(_param("VCPUS"), 4))
memory_limit_mib = int(os.getenv(_param("MEMORY_MIB"), 16384))
resized_width = os.getenv(_param("RESIZED_WIDTH"))
resized_height = os.getenv(_param("RESIZED_HEIGHT"))

batch_config = {
    "retries": retries,
    "timeout_seconds": timeout_seconds,
    "vcpus": vcpus,
    "memory_limit_mib": memory_limit_mib,
}

if resized_width:
    batch_config["resized_width"] = int(resized_width)

if resized_height:
    batch_config["resized_height"] = int(resized_height)

if not ecr_repository_arn:
    raise ValueError("ECR Repository ARN is missing.")

if not full_access_policy:
    raise ValueError("S3 Full Access Policy ARN is missing.")


def generate_description() -> str:
    soln_id = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_ID", None)
    soln_name = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_NAME", None)
    soln_version = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_VERSION", None)

    desc = "(SO9154) Autonomous Driving Data Framework (ADDF) - ros-to-png"
    if soln_id and soln_name and soln_version:
        desc = f"({soln_id}) {soln_name}. Version {soln_version}"
    elif soln_id and soln_name:
        desc = f"({soln_id}) {soln_name}"
    return desc


app = App()

stack = RosToPngBatchJob(
    scope=app,
    id=f"{project_name}-{deployment_name}-{module_name}",
    project_name=project_name,
    deployment_name=deployment_name,
    module_name=module_name,
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
    ecr_repository_arn=ecr_repository_arn,
    s3_access_policy=full_access_policy,
    batch_config=batch_config,
    stack_description=generate_description(),
)


CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "JobDefinitionArn": stack.batch_job.job_definition_arn,
        }
    ),
)

app.synth(force=True)
