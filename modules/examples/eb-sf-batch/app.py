# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

from aws_cdk import App, CfnOutput, Environment
from stack import EventDrivenBatch

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


vcpus = os.getenv(_param("VCPUS"))  # required
memory_limit_mib = os.getenv(_param("MEMORY_LIMIT_MIB"))  # required
fargate_job_queue_arn = os.getenv(_param("FARGATE_JOB_QUEUE_ARN"))  # required
ecr_repo_name = os.getenv(_param("ECR_REPO_NAME"))  # required


if not fargate_job_queue_arn:
    raise ValueError("Batch Queue Configuration is missing.")

if not ecr_repo_name:
    raise ValueError("ECR Repository Name is missing.")

app = App()

stack = EventDrivenBatch(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    fargate_job_queue_arn=fargate_job_queue_arn,
    ecr_repo_name=ecr_repo_name,
    vcpus=vcpus,  # type: ignore
    memory_limit_mib=memory_limit_mib,  # type: ignore
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "StateMachine": stack.eventbridge_sfn.state_machine.state_machine_arn,
        }
    ),
)

app.synth(force=True)
