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

import logging
import os
from typing import Any, cast

import aws_cdk
import cdk_nag
from aws_cdk import Aspects, Stack, Tags, aws_dynamodb, aws_s3
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class TfPreReqs(Stack):  # type: ignore
    def __init__(
        self,
        scope: Construct,
        id: str,
        deployment_name: str,
        module_name: str,
        hash: str,
        tf_s3_backend_encryption_type: str,
        tf_s3_backend_retention_type: str,
        tf_ddb_retention_type: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id, description="This stack deploys Storage resources for ADDF", **kwargs)
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{deployment_name}")

        # S3 bucket for storing the remote state of Terraform
        self.tf_state_s3bucket = aws_s3.Bucket(
            self,
            removal_policy=aws_cdk.RemovalPolicy.RETAIN
            if tf_s3_backend_retention_type.upper() == "RETAIN"
            else aws_cdk.RemovalPolicy.DESTROY,
            bucket_name=f"addf-{deployment_name}-tfstate-bucket-{hash}",
            id="tf-state-bucket",
            encryption=aws_s3.BucketEncryption.KMS_MANAGED
            if tf_s3_backend_encryption_type.upper() == "KMS"
            else aws_s3.BucketEncryption.S3_MANAGED,
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            versioned=True,
        )

        # DDB Table for storing the LockIDs of Terraform
        part_key = "LockID"
        self.tf_ddb_lock_table = aws_dynamodb.Table(
            self,
            "tf_ddb_lock_table",
            table_name=f"addf-{deployment_name}-tf-ddb-lock-table",
            partition_key=aws_dynamodb.Attribute(name=part_key, type=aws_dynamodb.AttributeType.STRING),
            billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=aws_cdk.RemovalPolicy.RETAIN
            if tf_ddb_retention_type.upper() == "RETAIN"
            else aws_cdk.RemovalPolicy.DESTROY,
        )

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        suppressions = [
            NagPackSuppression(
                **{
                    "id": "AwsSolutions-S1",
                    "reason": "Logging has been disabled for demo purposes",
                }
            ),
            NagPackSuppression(
                **{
                    "id": "AwsSolutions-IAM5",
                    "reason": "Resource access restriced to ADDF resources",
                }
            ),
        ]

        NagSuppressions.add_stack_suppressions(self, suppressions)
