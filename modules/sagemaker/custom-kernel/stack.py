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

from typing import Any

import cdk_nag
from aws_cdk import Aspects, Stack
from aws_cdk import aws_iam as iam
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct


class CustomKernelStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        app_prefix: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.sagemaker_studio_image_role = iam.Role(
            self,
            f"{app_prefix}-image-role",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
        )
        self.sagemaker_studio_image_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
        )
        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            apply_to_nested_stacks=True,
            suppressions=[
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-IAM4",
                        "reason": "Image Role needs Sagemaker Full Access",
                    }
                ),
            ],
        )
