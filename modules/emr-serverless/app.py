#!/usr/bin/env python3
import os
import aws_cdk
from aws_cdk import App, CfnOutput
from stack import EmrServerlessStack

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")

def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"

app = App()

emr_serverless = EmrServerlessStack(
    scope=app,
    construct_id=f"addf-{deployment_name}-{module_name}",
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"]
    ),
    deployment=deployment_name,
    module=module_name,
    )


CfnOutput(
    scope=emr_serverless,
    id="metadata",
    value=emr_serverless.to_json_string(
        {
            "EmrApplicationId": emr_serverless.emr_app.attr_application_id,
            "EmrJobExecutionRoleArn": emr_serverless.job_role.role_arn,
        }
    ),
)

app.synth()
