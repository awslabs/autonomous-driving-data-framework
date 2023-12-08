# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os
from typing import cast

from aws_cdk import App, CfnOutput, Environment

from stack import EmrServerlessStack

# Project specific
project_name = os.getenv("SEEDFARMER_PROJECT_NAME")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME")
module_name = os.getenv("SEEDFARMER_MODULE_NAME")

if len(f"{project_name}-{deployment_name}") > 36:
    raise ValueError("This module cannot support a project+deployment name character length greater than 35")


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


# App specific
vpc_id = os.getenv(_param("VPC_ID"))  # required
private_subnet_ids = json.loads(os.getenv(_param("PRIVATE_SUBNET_IDS"), ""))  # required

if not vpc_id:
    raise ValueError("Missing input parameter vpc-id")

if not private_subnet_ids:
    raise ValueError("Missing input parameter private-subnet-ids")


def generate_description() -> str:
    soln_id = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_ID", None)
    soln_name = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_NAME", None)
    soln_version = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_VERSION", None)

    desc = "IDF - EMR Serverless Module"
    if soln_id and soln_name and soln_version:
        desc = f"({soln_id}) {soln_name}. Version {soln_version}"
    elif soln_id and soln_name:
        desc = f"({soln_id}) {soln_name}"
    return desc


app = App()

emr_serverless = EmrServerlessStack(
    scope=app,
    id=f"{project_name}-{deployment_name}-{module_name}",
    project_name=cast(str, project_name),
    deployment_name=cast(str, deployment_name),
    module_name=cast(str, module_name),
    vpc_id=vpc_id,
    private_subnet_ids=private_subnet_ids,
    stack_description=generate_description(),
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)


CfnOutput(
    scope=emr_serverless,
    id="metadata",
    value=emr_serverless.to_json_string(
        {
            "EmrApplicationId": emr_serverless.emr_app.attr_application_id,
            "EmrJobExecutionRoleArn": emr_serverless.job_role.role_arn,
            "EmrSecurityGroupId": emr_serverless.emr_security_group.security_group_id,
            "EmrVpcId": vpc_id,
            "EmrSubnets": private_subnet_ids,
        }
    ),
)

app.synth()
