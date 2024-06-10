# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

from aws_cdk import App, CfnOutput, Environment, RemovalPolicy

from stack import RosToParquetBatchJob

project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


full_access_policy = os.getenv(_param("FULL_ACCESS_POLICY_ARN"))
platform = os.getenv(_param("PLATFORM"), "FARGATE")
retries = int(os.getenv(_param("RETRIES"), 1))
timeout_seconds = int(os.getenv(_param("TIMEOUT_SECONDS"), 60))
vcpus = int(os.getenv(_param("VCPUS"), 4))
memory_limit_mib = int(os.getenv(_param("MEMORY_MIB"), 16384))
removal_policy = os.getenv(_param("REMOVAL_POLICY"), "")

if not full_access_policy:
    raise ValueError("S3 Full Access Policy ARN is missing.")


if platform not in ["FARGATE", "EC2"]:
    raise ValueError("Platform must be either FARGATE or EC2")


def generate_description() -> str:
    soln_id = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_ID", None)
    soln_name = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_NAME", None)
    soln_version = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_VERSION", None)

    desc = "(SO9154) Autonomous Driving Data Framework (ADDF) - ros-to-parquet"
    if soln_id and soln_name and soln_version:
        desc = f"({soln_id}) {soln_name}. Version {soln_version}"
    elif soln_id and soln_name:
        desc = f"({soln_id}) {soln_name}"
    return desc


app = App()

stack = RosToParquetBatchJob(
    scope=app,
    id=f"{project_name}-{deployment_name}-{module_name}",
    project_name=project_name,
    deployment_name=deployment_name,
    module_name=module_name,
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
    platform=platform,
    retries=retries,
    timeout_seconds=timeout_seconds,
    vcpus=vcpus,
    memory_limit_mib=memory_limit_mib,
    s3_access_policy=full_access_policy,
    stack_description=generate_description(),
    removal_policy=RemovalPolicy.RETAIN if removal_policy.upper() == "RETAIN" else RemovalPolicy.DESTROY,
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
