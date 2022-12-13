import os

import aws_cdk
from aws_cdk import App, Aws, CfnOutput

from stack import Cloud9Stack

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME")
module_name = os.getenv("ADDF_MODULE_NAME")

def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"

image_id = os.getenv(_param("IMAGE_ID"), "ami-0beaa649c482330f7")
instance_stop_time_minutes = int(os.getenv(_param("INSTANCE_STOP_TIME_MINUTES"), 60))
instance_type = os.getenv(_param("INSTANCE_TYPE"), "t3.small")
name = os.getenv(_param("NAME"), "cloud9env")
owner_role = os.getenv(_param("OWNER_ROLE"), None)
storage_size = os.getenv(_param("STORAGE_SIZE"), 20)
subnet_id = os.getenv(_param("SUBNET_ID"), None)

if owner_role is None:
    raise ValueError("owner role must not be empty. You will not be able to access your env")

if subnet_id is None:
    raise ValueError("subnet_id must not be empty")

owner_arn = f"arn:aws:iam::{Aws.ACCOUNT_ID}:{owner_role}"

app = App()

stack = Cloud9Stack(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    image_id=image_id,
    instance_stop_time_minutes=instance_stop_time_minutes,
    instance_type=instance_type,
    name=name,
    owner_arn=owner_arn,
    subnet_id=subnet_id,
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
            "Cloud9EnvName": stack.cloud9_instance.attr_name,
            "Cloud9EnvArn": stack.cloud9_instance.attr_arn,
            "InstanceStorageSize": storage_size,
        }
    ),
)

app.synth(force=True)
