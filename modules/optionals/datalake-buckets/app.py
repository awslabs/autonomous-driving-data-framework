# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

import aws_cdk
from aws_cdk import App, CfnOutput

from stack import DataLakeBucketsStack

# ADDF vars
deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")
hash = os.getenv("ADDF_HASH", "")

# App Env vars
buckets_encryption_type = os.getenv("ADDF_PARAMETER_ENCRYPTION_TYPE", "SSE")
buckets_retention = os.getenv("ADDF_PARAMETER_RETENTION_TYPE", "DESTROY")
artifact_logs_retention = os.getenv("ADDF_PARAMETER_ARTIFACTS_LOG_RETENTION", "1")

if buckets_retention not in ["DESTROY", "RETAIN"]:
    raise ValueError("The only RETENTION_TYPE values accepted are 'DESTROY' and 'RETAIN' ")


if buckets_encryption_type not in ["SSE", "KMS"]:
    raise ValueError("The only ENCRYPTION_TYPE values accepted are 'SSE' and 'KMS' ")


def generate_description() -> str:
    soln_id = os.getenv("ADDF_PARAMETER_SOLUTION_ID", None)
    soln_name = os.getenv("ADDF_PARAMETER_SOLUTION_NAME", None)
    soln_version = os.getenv("ADDF_PARAMETER_SOLUTION_VERSION", None)

    desc = "ADDF - Datalake Buckets Module"
    if soln_id and soln_name and soln_version:
        desc = f"({soln_id}) {soln_name}. Version {soln_version}"
    elif soln_id and soln_name:
        desc = f"({soln_id}) {soln_name}"
    return desc


app = App()


stack = DataLakeBucketsStack(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    hash=hash,
    buckets_encryption_type=buckets_encryption_type,
    buckets_retention=buckets_retention,
    artifacts_log_retention=int(artifact_logs_retention),
    stack_description=generate_description(),
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
            "ArtifactsBucketName": stack.artifacts_bucket.bucket_name,
            "LogsBucketName": stack.logs_bucket.bucket_name,
            "RawBucketName": stack.raw_bucket.bucket_name,
            "IntermediateBucketName": stack.intermediate_bucket.bucket_name,
            "CuratedBucketName": stack.curated_bucket.bucket_name,
            "ReadOnlyPolicyArn": stack.readonly_policy.managed_policy_arn,
            "FullAccessPolicyArn": stack.fullaccess_policy.managed_policy_arn,
        }
    ),
)


app.synth(force=True)
