# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

from aws_cdk import App, CfnOutput, Environment

from stack import ImageExtraction

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


retries = int(os.getenv(_param("RETRIES"), 1))
timeout_seconds = int(os.getenv(_param("TIMEOUT_SECONDS"), 60))  # optional
# start_range = os.getenv(_param("START_RANGE"))  # optional
# end_range = os.getenv(_param("END_RANGE"))  # optional
vcpus = int(os.getenv(_param("VCPUS"), 4))
memory_limit_mib = int(os.getenv(_param("MEMORY_MIB"), 16384))
on_demand_job_queue_arn = os.getenv(_param("ON_DEMAND_JOB_QUEUE_ARN"))  # required
repository_name = os.getenv(_param("REPOSITORY_NAME"))  # required
artifacts_bucket_name = os.getenv(_param("ARTIFACTS_BUCKET_NAME"))
platform = os.getenv(_param("PLATFORM"), "EC2")

if not on_demand_job_queue_arn:
    raise ValueError("Batch Queue Configuration is missing.")

if not repository_name:
    raise ValueError("ECR Repository Name is missing.")

if not artifacts_bucket_name:
    raise ValueError("S3 Bucket is missing.")

if platform not in ["FARGATE", "EC2"]:
    raise ValueError("Platform must be either FARGATE or EC2")

app = App()

stack = ImageExtraction(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    retries=retries,
    timeout_seconds=timeout_seconds,
    vcpus=vcpus,
    memory_limit_mib=memory_limit_mib,
    repository_name=repository_name,
    artifacts_bucket_name=artifacts_bucket_name,
    on_demand_job_queue_arn=on_demand_job_queue_arn,
    platform=platform,
    # start_range=start_range,
    # end_range=end_range,
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)


CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {"BatchExecutionRoleArn": stack.role.role_arn, "ImageExtractionDkrImageUri": stack.image_uri}
    ),
)

app.synth(force=True)
