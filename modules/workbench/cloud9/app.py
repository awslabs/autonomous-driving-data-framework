import os

import aws_cdk
import boto3
from aws_cdk import App, CfnOutput

from stack import Cloud9Stack


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


def is_ami_valid(image_id: str) -> None:
    if image_id.startswith("ami"):
        ssmc = boto3.client("ssm")
        cloud9_params = ssmc.get_parameters_by_path(Path="/aws/service/cloud9", Recursive=True)

        for param in cloud9_params.get("Parameters", []):
            if param["Value"] == image_id:
                image_id = f"resolve:ssm:{param['Name']}"
                break
        else:
            raise ValueError(
                (
                    f"The AMI provided `{image_id}` is not a valid AMI supported by Cloud9. "
                    "For a list of valid images, check the README or run the following command: "
                    "`aws ssm get-parameters-by-path --path '/aws/service/cloud9' --recursive` "
                )
            )


deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME")
module_name = os.getenv("ADDF_MODULE_NAME")
connection_type = os.getenv(_param("CONNECTION_TYPE"), "CONNECT_SSM")
image_id = os.getenv(_param("IMAGE_ID"), "ubuntu-18.04-x86_64")
instance_stop_time_minutes = int(os.getenv(_param("INSTANCE_STOP_TIME_MINUTES"), 60))
instance_type = os.getenv(_param("INSTANCE_TYPE"), None)
name = os.getenv(_param("INSTANCE_NAME"), "cloud9env")
owner_arn = os.getenv(_param("OWNER_ARN"), None)
storage_size = os.getenv(_param("STORAGE_SIZE"), 20)
subnet_id = os.getenv(_param("SUBNET_ID"), None)

is_ami_valid(image_id=image_id)

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
    connection_type=connection_type,
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
