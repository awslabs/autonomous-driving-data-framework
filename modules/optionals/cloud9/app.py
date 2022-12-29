import os

import aws_cdk
from aws_cdk import App, Aws, CfnOutput

from stack import Cloud9Stack

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME")
module_name = os.getenv("ADDF_MODULE_NAME")

def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"

image_id = os.getenv(_param("IMAGE_ID"), None)
instance_stop_time_minutes = int(os.getenv(_param("INSTANCE_STOP_TIME_MINUTES"), 60))
instance_type = os.getenv(_param("INSTANCE_TYPE"), None)
name = os.getenv(_param("NAME"), "cloud9env")
owner_arn = os.getenv(_param("OWNER_ARN"), None)
storage_size = os.getenv(_param("STORAGE_SIZE"), 20)
subnet_id = os.getenv(_param("SUBNET_ID"), None)

if image_id is None:
    raise ValueError("Parameter `image_id` not found.")

if instance_type is None:
    raise ValueError("Parameter `instance_type` not found.")

if owner_arn is None:
    raise ValueError("Parameter `owner_arn` not found. You will not be able to access your env")

if subnet_id is None:
    raise ValueError("Parameter `subnet_id` not found")

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
