import time

from aws_cdk import CfnOutput, Stack, aws_iam as iam
from constructs import Construct

class CustomKernelStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        app_prefix: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        sagemaker_studio_image_role = iam.Role(
            self,
            f"{app_prefix}-image-role",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
        )
        sagemaker_studio_image_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
        )

        CfnOutput(
            self,
            "SageMakerCustomKernelRoleArn",
            value=sagemaker_studio_image_role.role_arn,
        )
