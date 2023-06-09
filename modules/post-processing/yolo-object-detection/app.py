import os

from aws_cdk import App, CfnOutput, Environment
from stack import ObjectDetection

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


full_access_policy = os.getenv(_param("FULL_ACCESS_POLICY_ARN"))

if not full_access_policy:
    raise ValueError("S3 Full Access Policy ARN is missing.")

app = App()

stack = ObjectDetection(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
    s3_access_policy=full_access_policy,
)

base_image = (
    f"763104351884.dkr.ecr.{stack.region}.amazonaws.com/pytorch-inference:1.12.1-gpu-py38-cu113-ubuntu20.04-sagemaker"
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "ImageUri": stack.image_uri,
            "EcrRepoName": stack.repository_name,
            "ExecutionRole": stack.role.role_arn,
            "BaseImage": base_image,
        }
    ),
)

app.synth(force=True)
