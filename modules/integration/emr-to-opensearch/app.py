# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os

import aws_cdk
import cdk_nag

from stack import EMRtoOpensearch

project_name = os.getenv("SEEDFARMER_PROJECT_NAME", "")
deployment_name = os.getenv("SEEDFARMER_DEPLOYMENT_NAME", "")
module_name = os.getenv("SEEDFARMER_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"SEEDFARMER_PARAMETER_{name}"


vpc_id = os.getenv(_param("VPC_ID"))  # required
private_subnet_ids = json.loads(os.getenv(_param("PRIVATE_SUBNET_IDS"), ""))  # required

opensearch_sg_id = os.getenv(_param("OPENSEARCH_SG_ID"), "")
opensearch_domain_name = os.getenv(_param("OPENSEARCH_DOMAIN_NAME"), "")
opensearch_domain_endpoint = os.getenv(_param("OPENSEARCH_DOMAIN_ENDPOINT"), "")
logs_bucket_name = os.getenv(_param("LOGS_BUCKET_NAME"), "")
emr_logs_prefix = os.getenv(_param("EMR_LOGS_PREFIX"), "")

if not vpc_id:
    raise Exception("missing input parameter vpc-id")

if not private_subnet_ids:
    raise Exception("missing input parameter private-subnet-ids")

app = aws_cdk.App()

stack = EMRtoOpensearch(
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
    logs_bucket_name=logs_bucket_name,
    emr_logs_prefix=emr_logs_prefix,
)

aws_cdk.CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "LambdaName": stack.lambda_name,
            "LambdaArn": stack.lambda_arn,
        }
    ),
)

aws_cdk.Aspects.of(app).add(cdk_nag.AwsSolutionsChecks(log_ignores=True))

app.synth(force=True)
