#!/usr/bin/env python3
import json
import os

import aws_cdk as cdk
import boto3
from pipeline import PipelineStack

config_file = open("../.sagemaker-code-config")
sagemaker_code_config = json.load(config_file)
sagemaker_project_name = sagemaker_code_config["sagemakerProjectName"]
sagemaker_project_id = sagemaker_code_config["sagemakerProjectId"]
sagemaker_repository_name = sagemaker_code_config["codeRepositoryName"]
sagemaker_pipeline_name = sagemaker_code_config["sagemakerPipelineName"]
project_short_name = sagemaker_code_config["projectShortName"]
env_name = "dev"
model_package_group_name = f"{sagemaker_pipeline_name}-{env_name}-models"


def get_account() -> str:
    if "CDK_DEFAULT_ACCOUNT" in os.environ:
        return os.environ["CDK_DEFAULT_ACCOUNT"]
    return boto3.client(service_name="sts").get_caller_identity().get("Account")


def get_region() -> str:
    if "CDK_DEFAULT_REGION" in os.environ:
        return os.environ["CDK_DEFAULT_REGION"]
    session = boto3.Session()
    if session.region_name is None:
        raise ValueError(
            "It is not possible to infer AWS REGION from your environment. Please pass the --region argument.",
        )
    return str(session.region_name)


app = cdk.App()

PipelineStack(
    app,
    f"mlops-pipeline-{sagemaker_project_name}-{sagemaker_project_id}",
    code_repository_name=sagemaker_repository_name,
    sagemaker_project_name=sagemaker_project_name,
    sagemaker_project_id=sagemaker_project_id,
    model_package_group_name=model_package_group_name,
    project_short_name=project_short_name,
    env_name=env_name,
    env=cdk.Environment(
        account=get_account(),
        region=get_region(),
    ),
)
app.synth()
