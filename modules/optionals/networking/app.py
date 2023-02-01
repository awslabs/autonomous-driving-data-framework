import os
from typing import cast

import aws_cdk
from aws_cdk import App, CfnOutput

from stack import NetworkingStack

project_name = os.getenv("AWS_CODESEEDER_NAME", "addf")


def _proj(name: str) -> str:
    return f"{project_name.upper()}_{name}"


def _param(name: str) -> str:
    return f"{project_name.upper()}_PARAMETER_{name}"


deployment_name = os.getenv(_proj("DEPLOYMENT_NAME"))
module_name = os.getenv(_proj("MODULE_NAME"))
internet_accessible = os.getenv(_param("INTERNET_ACCESSIBLE"))

app = App()

stack = NetworkingStack(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=cast(str, deployment_name),
    module_name=cast(str, module_name),
    internet_accessible=cast(bool, internet_accessible),
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
            "IsolatedSubnetIds": stack.isolated_subnets.subnet_ids if not internet_accessible else None,
        }
    ),
)

app.synth(force=True)
