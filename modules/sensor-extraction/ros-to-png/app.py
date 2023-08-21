# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

from aws_cdk import App, CfnOutput, Environment
from stack import RosToPngBatchJob

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


full_access_policy = os.getenv(_param("FULL_ACCESS_POLICY_ARN"))
retries = int(os.getenv(_param("RETRIES"), 1))
timeout_seconds = int(os.getenv(_param("TIMEOUT_SECONDS"), 60))
vcpus = int(os.getenv(_param("VCPUS"), 4))
memory_limit_mib = int(os.getenv(_param("MEMORY_MIB"), 16384))
resized_width = os.getenv(_param("RESIZED_WIDTH"))
resized_height = os.getenv(_param("RESIZED_HEIGHT"))

if resized_width:
    resized_width = int(resized_width)  # type: ignore

if resized_height:
    resized_height = int(resized_height)  # type: ignore

if not full_access_policy:
    raise ValueError("S3 Full Access Policy ARN is missing.")

app = App()

stack = RosToPngBatchJob(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
    retries=retries,
    timeout_seconds=timeout_seconds,
    vcpus=vcpus,
    memory_limit_mib=memory_limit_mib,
    s3_access_policy=full_access_policy,
    resized_width=resized_width,  # type: ignore
    resized_height=resized_height,  # type: ignore
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
