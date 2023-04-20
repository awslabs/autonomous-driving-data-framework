import json
import os
from typing import cast

import aws_cdk
from aws_cdk import App, CfnOutput

from stack import NetworkingStack

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME")
module_name = os.getenv("ADDF_MODULE_NAME")
internet_accessible = json.loads(os.getenv("ADDF_PARAMETER_INTERNET_ACCESSIBLE", "true"))

app = App()

stack = NetworkingStack(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=cast(str, deployment_name),
    module_name=cast(str, module_name),
    internet_accessible=internet_accessible,
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "VpcId": stack.vpc.vpc_id,
            "PublicSubnetIds": stack.public_subnets.subnet_ids,
            "PrivateSubnetIds": stack.private_subnets.subnet_ids,
            "IsolatedSubnetIds": stack.isolated_subnets.subnet_ids if not stack.internet_accessible else [],
        }
    ),
)

app.synth(force=True)
