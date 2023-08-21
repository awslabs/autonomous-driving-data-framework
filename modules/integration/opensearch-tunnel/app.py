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

import os

import aws_cdk
from aws_cdk import App, CfnOutput

from stack import TunnelStack

account = os.environ["CDK_DEFAULT_ACCOUNT"]
region = os.environ["CDK_DEFAULT_REGION"]

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


vpc_id = os.getenv(_param("VPC_ID"))
opensearch_sg_id = os.getenv(_param("OPENSEARCH_SG_ID"))
opensearch_domain_endpoint = os.getenv(_param("OPENSEARCH_DOMAIN_ENDPOINT"))

if not vpc_id:
    raise ValueError("missing input parameter vpc-id")

if not opensearch_sg_id:
    raise ValueError("missing input parameter opensearch_sg_id")

if not opensearch_domain_endpoint:
    raise ValueError("missing input parameter opensearch_domain_endpoint")


port = int(os.getenv(_param("PORT"), "3000"))

project_dir = os.path.dirname(os.path.abspath(__file__))
install_script = os.path.join(project_dir, "install_nginx.sh")


app = App()

stack = TunnelStack(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    env=aws_cdk.Environment(
        account=account,
        region=region,
    ),
    deployment=deployment_name,
    module=module_name,
    vpc_id=vpc_id,
    opensearch_sg_id=opensearch_sg_id,
    opensearch_domain_endpoint=opensearch_domain_endpoint,
    install_script=install_script,
    port=port,
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "OpenSearchTunnelInstanceId": stack.instance_id,
            "OpenSearchTunnelUrl": stack.dashboard_url,
            "OpenSearchTunnelPort": port,
            "SampleSSMCommand": stack.command,
        }
    ),
)


app.synth(force=True)
