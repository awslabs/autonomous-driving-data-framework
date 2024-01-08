# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os

from aws_cdk import App, CfnOutput, Environment
from stack import BatchDags

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


vpc_id = os.getenv(_param("VPC_ID"))  # required
private_subnet_ids = json.loads(os.getenv(_param("PRIVATE_SUBNET_IDS"), ""))  # required
batch_compute = json.loads(os.getenv(_param("BATCH_COMPUTE"), ""))  # required
mwaa_exec_role = os.getenv(_param("MWAA_EXEC_ROLE"))

if not vpc_id:
    raise Exception("missing input parameter vpc-id")

if not private_subnet_ids:
    raise Exception("missing input parameter private-subnet-ids")

if not batch_compute:
    raise ValueError("Batch Compute Configuration is missing.")

if not mwaa_exec_role:
    raise ValueError("MWAA Execution Role is missing.")

app = App()

stack = BatchDags(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    mwaa_exec_role=mwaa_exec_role,
    vpc_id=vpc_id,
    private_subnet_ids=private_subnet_ids,
    batch_compute=batch_compute,
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
            "DagRoleArn": stack.dag_role.role_arn,
            "OnDemandJobQueueArn": stack.on_demand_jobqueue.job_queue_arn
            if stack.on_demand_jobqueue.job_queue_arn
            else "QUEUE NOT CREATED",
            "SpotJobQueueArn": stack.spot_jobqueue.job_queue_name
            if stack.spot_jobqueue.job_queue_name
            else "QUEUE NOT CREATED",
            "FargateJobQueueArn": stack.spot_jobqueue.job_queue_name
            if stack.fargate_jobqueue.job_queue_name
            else "QUEUE NOT CREATED",
        }
    ),
)

app.synth(force=True)
