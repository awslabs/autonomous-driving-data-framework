# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os

import aws_cdk
from aws_cdk import App, CfnOutput

from stack import DDBtoOpensearch

project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


vpc_id = os.getenv(_param("VPC_ID"))
private_subnet_ids_param = os.getenv(_param("PRIVATE_SUBNET_IDS"))

if not vpc_id:
    raise ValueError("missing input parameter vpc-id")

if not private_subnet_ids_param:
    raise ValueError("missing input parameter private-subnet-ids")
else:
    private_subnet_ids = json.loads(private_subnet_ids_param)

opensearch_sg_id = os.getenv(_param("OPENSEARCH_SG_ID"), "")
opensearch_domain_name = os.getenv(_param("OPENSEARCH_DOMAIN_NAME"), "")
opensearch_domain_endpoint = os.getenv(_param("OPENSEARCH_DOMAIN_ENDPOINT"), "")
ddb_stream_arn = os.getenv(_param("ROSBAG_STREAM_ARN"), "")


def generate_description() -> str:
    soln_id = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_ID", None)
    soln_name = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_NAME", None)
    soln_version = os.getenv("SEEDFARMER_PARAMETER_SOLUTION_VERSION", None)

    desc = "DDB to OpenSearch Module"
    if soln_id and soln_name and soln_version:
        desc = f"({soln_id}) {soln_name}. Version {soln_version}"
    elif soln_id and soln_name:
        desc = f"({soln_id}) {soln_name}"
    return desc


app = App()

stack = DDBtoOpensearch(
    scope=app,
    id=f"{project_name}-{deployment_name}-{module_name}",
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
    project=project_name,
    deployment=deployment_name,
    module=module_name,
    vpc_id=vpc_id,
    private_subnet_ids=private_subnet_ids,
    opensearch_sg_id=opensearch_sg_id,
    opensearch_domain_endpoint=opensearch_domain_endpoint,
    opensearch_domain_name=opensearch_domain_name,
    ddb_stream_arn=ddb_stream_arn,
    stack_description=generate_description(),
)


CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "LambdaName": stack.lambda_name,
            "LambdaArn": stack.lambda_arn,
        }
    ),
)


app.synth(force=True)
