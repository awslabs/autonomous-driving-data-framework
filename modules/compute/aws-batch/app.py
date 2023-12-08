# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os

from aws_cdk import App, CfnOutput, Environment

from stack import AwsBatch

# Project specific
project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")

if len(f"{project_name}-{deployment_name}") > 36:
    raise ValueError("This module cannot support a project+deployment name character length greater than 35")


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


# App specific
vpc_id = os.getenv(_param("VPC_ID"))  # required
private_subnet_ids = json.loads(os.getenv(_param("PRIVATE_SUBNET_IDS"), ""))  # required
batch_compute = json.loads(os.getenv(_param("BATCH_COMPUTE"), ""))  # required

if not vpc_id:
    raise ValueError("Missing input parameter vpc-id")

if not private_subnet_ids:
    raise ValueError("Missing input parameter private-subnet-ids")

if not batch_compute:
    raise ValueError("Batch Compute Configuration is missing.")


def generate_description() -> str:
    soln_id = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_ID", None)
    soln_name = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_NAME", None)
    soln_version = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_VERSION", None)

    desc = "IDF - AWS Batch Module"
    if soln_id and soln_name and soln_version:
        desc = f"({soln_id}) {soln_name}. Version {soln_version}"
    elif soln_id and soln_name:
        desc = f"({soln_id}) {soln_name}"
    return desc


app = App()

stack = AwsBatch(
    scope=app,
    id=f"{project_name}-{deployment_name}-{module_name}",
    project_name=project_name,
    deployment_name=deployment_name,
    module_name=module_name,
    vpc_id=vpc_id,
    private_subnet_ids=private_subnet_ids,
    batch_compute=batch_compute,
    stack_description=generate_description(),
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
            "BatchPolicyString": stack.batch_policy_document,
            "BatchSecurityGroupId": stack.batch_sg,
            "OnDemandJobQueueArn": stack.on_demand_jobqueue.job_queue_arn
            if stack.on_demand_jobqueue
            else "QUEUE NOT CREATED",
            "SpotJobQueueArn": stack.spot_jobqueue.job_queue_name if stack.spot_jobqueue else "QUEUE NOT CREATED",
            "FargateJobQueueArn": stack.fargate_jobqueue.job_queue_name
            if stack.fargate_jobqueue
            else "QUEUE NOT CREATED",
        }
    ),
)

app.synth(force=True)
