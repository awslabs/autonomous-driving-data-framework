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

from aws_cdk import App, CfnOutput, Environment

from stack import LaneDetection

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


full_access_policy = os.getenv(_param("FULL_ACCESS_POLICY_ARN"))

if not full_access_policy:
    raise ValueError("S3 Full Access Policy ARN is missing.")

app = App()

stack = LaneDetection(
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


CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "ImageUri": stack.image_uri,
            "EcrRepoName": stack.repository_name,
            "ExecutionRole": stack.role.role_arn,
        }
    ),
)

app.synth(force=True)
