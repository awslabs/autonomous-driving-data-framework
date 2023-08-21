#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License").
#    You may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import json
import os

import aws_cdk
from aws_cdk import App, CfnOutput

from stack import DDBtoOpensearch

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


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


app = App()

stack = DDBtoOpensearch(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
    deployment=deployment_name,
    module=module_name,
    vpc_id=vpc_id,
    private_subnet_ids=private_subnet_ids,
    opensearch_sg_id=opensearch_sg_id,
    opensearch_domain_endpoint=opensearch_domain_endpoint,
    opensearch_domain_name=opensearch_domain_name,
    ddb_stream_arn=ddb_stream_arn,
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
