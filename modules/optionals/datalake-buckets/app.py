#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License").
#    You may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

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

if buckets_retention not in ["DESTROY", "RETAIN"]:
    raise ValueError("The only RETENTION_TYPE values accepted are 'DESTROY' and 'RETAIN' ")


if buckets_encryption_type not in ["SSE", "KMS"]:
    raise ValueError("The only ENCRYPTION_TYPE values accepted are 'SSE' and 'KMS' ")


app = App()


stack = DataLakeBucketsStack(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    hash=hash,
    buckets_encryption_type=buckets_encryption_type,
    buckets_retention=buckets_retention,
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
