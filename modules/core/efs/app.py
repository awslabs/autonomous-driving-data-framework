import os
from typing import cast

import aws_cdk
from aws_cdk import App, CfnOutput

from stack_efs import EFSFileStorage

project_name = os.getenv("AWS_CODESEEDER_NAME", "addf")


def _proj(name: str) -> str:
    return f"{project_name.upper()}_{name}"


def _param(name: str) -> str:
    return f"{project_name.upper()}_PARAMETER_{name}"


def evaluate_removal_policy() -> str:
    return "DESTROY" if os.getenv(_param("REMOVAL_POLICY"), "RETAIN").upper() in ["DESTROY"] else "RETAIN"


deployment_name = os.getenv(_proj("DEPLOYMENT_NAME"))
module_name = os.getenv(_proj("MODULE_NAME"))
vpc_id = os.getenv(_param("VPC_ID"))
efs_removal_policy = evaluate_removal_policy()

if not vpc_id:
    raise Exception("missing input parameter vpc-id")

app = App()


efs_stack = EFSFileStorage(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=cast(str, deployment_name),
    module_name=cast(str, module_name),
    vpc_id=vpc_id,
    efs_removal_policy=efs_removal_policy,
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)
CfnOutput(
    scope=efs_stack,
    id="metadata",
    value=efs_stack.to_json_string(
        {
            "EFSFileSystemId": efs_stack.efs_filesystem.file_system_id,
            "EFSFileSystemArn": efs_stack.efs_filesystem.file_system_arn,
            "EFSSecurityGroupId": efs_stack.efs_security_group.security_group_id,
            "VPCId": efs_stack.vpc_id,
        }
    ),
)


app.synth(force=True)
