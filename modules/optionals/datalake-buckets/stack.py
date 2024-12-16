# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import hashlib
import logging
from typing import Any, cast

import aws_cdk
import aws_cdk.aws_iam as aws_iam
import aws_cdk.aws_s3 as aws_s3
import cdk_nag
from aws_cdk import Aspects, Duration, Stack, Tags
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class DataLakeBucketsStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        project_name: str,
        deployment_name: str,
        module_name: str,
        hash: str,
        buckets_encryption_type: str,
        buckets_retention: str,
        artifacts_log_retention: int,
        stack_description: str,
        **kwargs: Any,
    ) -> None:
        # CDK Env Vars
        account: str = aws_cdk.Aws.ACCOUNT_ID
        region: str = aws_cdk.Aws.REGION
        partition: str = aws_cdk.Aws.PARTITION

        dep_mod = f"{project_name}-{deployment_name}-{module_name}"
        # used to tag AWS resources. Tag Value length cant exceed 256 characters
        full_dep_mod = dep_mod[:256] if len(dep_mod) > 256 else dep_mod

        super().__init__(scope, id, description=stack_description, **kwargs)
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=full_dep_mod)

        logs_bucket_name = f"{project_name}-{deployment_name}-logs-bucket-{hash}"
        hashlib.sha256()
        unique_ab = (hashlib.sha256(module_name.encode("utf-8")).hexdigest())[: (60 - len(logs_bucket_name))]

        logs_bucket = aws_s3.Bucket(
            self,
            id="logs-bucket",
            bucket_name=f"{logs_bucket_name}-{unique_ab}",
            removal_policy=aws_cdk.RemovalPolicy.RETAIN
            if buckets_retention.upper() == "RETAIN"
            else aws_cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=None if buckets_retention.upper() == "RETAIN" else True,
            # Encryption should be always set to AES256 for a bucket to receive access logging from target buckets
            encryption=aws_s3.BucketEncryption.S3_MANAGED,
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            object_ownership=aws_s3.ObjectOwnership.BUCKET_OWNER_PREFERRED,
            enforce_ssl=True,
            # MWAA is very chatty, logs need to be cleaned via LifecycleRule
            lifecycle_rules=[
                aws_s3.LifecycleRule(
                    expiration=Duration.days(artifacts_log_retention),
                    enabled=True,
                    prefix="artifacts-bucket-logs/",
                )
            ],
        )

        raw_bucket_name = f"{project_name}-{deployment_name}-raw-bucket-{hash}"
        unique_ab = (hashlib.sha256(module_name.encode("utf-8")).hexdigest())[: (60 - len(raw_bucket_name))]

        raw_bucket = aws_s3.Bucket(
            self,
            removal_policy=aws_cdk.RemovalPolicy.RETAIN
            if buckets_retention.upper() == "RETAIN"
            else aws_cdk.RemovalPolicy.DESTROY,
            bucket_name=f"{raw_bucket_name}-{unique_ab}",
            versioned=True,
            server_access_logs_bucket=logs_bucket,
            server_access_logs_prefix="raw-bucket-logs/",
            auto_delete_objects=None if buckets_retention.upper() == "RETAIN" else True,
            id="raw-bucket",
            encryption=aws_s3.BucketEncryption.KMS_MANAGED
            if buckets_encryption_type.upper() == "KMS"
            else aws_s3.BucketEncryption.S3_MANAGED,
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

        intermediate_bucket_name = f"{project_name}-{deployment_name}-intermediate-bucket-{hash}"
        unique_ab = (hashlib.sha256(module_name.encode("utf-8")).hexdigest())[: (60 - len(intermediate_bucket_name))]

        intermediate_bucket = aws_s3.Bucket(
            self,
            id="intermediate-bucket",
            removal_policy=aws_cdk.RemovalPolicy.RETAIN
            if buckets_retention.upper() == "RETAIN"
            else aws_cdk.RemovalPolicy.DESTROY,
            bucket_name=f"{intermediate_bucket_name}-{unique_ab}",
            versioned=True,
            server_access_logs_bucket=logs_bucket,
            server_access_logs_prefix="intermediate-bucket-logs/",
            auto_delete_objects=None if buckets_retention.upper() == "RETAIN" else True,
            encryption=aws_s3.BucketEncryption.KMS_MANAGED
            if buckets_encryption_type.upper() == "KMS"
            else aws_s3.BucketEncryption.S3_MANAGED,
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

        curated_bucket_name = f"{project_name}-{deployment_name}-curated-bucket-{hash}"
        unique_ab = (hashlib.sha256(module_name.encode("utf-8")).hexdigest())[: (60 - len(curated_bucket_name))]

        curated_bucket = aws_s3.Bucket(
            self,
            id="curated-bucket",
            removal_policy=aws_cdk.RemovalPolicy.RETAIN
            if buckets_retention.upper() == "RETAIN"
            else aws_cdk.RemovalPolicy.DESTROY,
            bucket_name=f"{curated_bucket_name}-{unique_ab}",
            versioned=True,
            server_access_logs_bucket=logs_bucket,
            server_access_logs_prefix="curated-bucket-logs/",
            auto_delete_objects=None if buckets_retention.upper() == "RETAIN" else True,
            encryption=aws_s3.BucketEncryption.KMS_MANAGED
            if buckets_encryption_type.upper() == "KMS"
            else aws_s3.BucketEncryption.S3_MANAGED,
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

        artifacts_bucket_name = f"{project_name}-{deployment_name}-artifacts-bucket-{hash}"
        unique_ab = (hashlib.sha256(module_name.encode("utf-8")).hexdigest())[: (60 - len(artifacts_bucket_name))]

        artifacts_bucket = aws_s3.Bucket(
            self,
            id="artifacts-bucket",
            bucket_name=f"{artifacts_bucket_name}-{unique_ab}",
            removal_policy=aws_cdk.RemovalPolicy.RETAIN
            if buckets_retention.upper() == "RETAIN"
            else aws_cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=None if buckets_retention.upper() == "RETAIN" else True,
            encryption=aws_s3.BucketEncryption.KMS_MANAGED
            if buckets_encryption_type.upper() == "KMS"
            else aws_s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            server_access_logs_bucket=logs_bucket,
            server_access_logs_prefix="artifacts-bucket-logs/",
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

        # ReadOnly IAM Policy
        readonly_policy = aws_iam.ManagedPolicy(
            self,
            id="readonly_policy",
            managed_policy_name=f"{project_name}-{deployment_name}-{module_name}-{region}-{account}-readonly-access",
            statements=[
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        "kms:Decrypt",
                        "kms:Encrypt",
                        "kms:ReEncrypt*",
                        "kms:DescribeKey",
                        "kms:GenerateDataKey",
                    ],
                    resources=[f"arn:{partition}:kms::{account}:*"],
                ),
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        "s3:GetObject",
                        "s3:GetObjectAcl",
                        "s3:ListBucket",
                    ],
                    resources=[
                        f"{raw_bucket.bucket_arn}/*",
                        f"{raw_bucket.bucket_arn}",
                        f"{intermediate_bucket.bucket_arn}/*",
                        f"{intermediate_bucket.bucket_arn}",
                        f"{curated_bucket.bucket_arn}/*",
                        f"{curated_bucket.bucket_arn}",
                        f"{artifacts_bucket.bucket_arn}/*",
                        f"{artifacts_bucket.bucket_arn}",
                    ],
                ),
            ],
        )

        # FullAccess IAM Policy
        fullaccess_policy = aws_iam.ManagedPolicy(
            self,
            id="fullaccess_policy",
            managed_policy_name=f"{project_name}-{deployment_name}-{module_name}-{region}-{account}-full-access",
            statements=[
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        "kms:Decrypt",
                        "kms:Encrypt",
                        "kms:ReEncrypt*",
                        "kms:DescribeKey",
                        "kms:GenerateDataKey",
                    ],
                    resources=[f"arn:{partition}:kms::{account}:*"],
                ),
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        "s3:GetObject",
                        "s3:GetObjectAcl",
                        "s3:ListBucket",
                    ],
                    resources=[
                        f"{raw_bucket.bucket_arn}/*",
                        f"{raw_bucket.bucket_arn}",
                        f"{intermediate_bucket.bucket_arn}/*",
                        f"{intermediate_bucket.bucket_arn}",
                        f"{curated_bucket.bucket_arn}/*",
                        f"{curated_bucket.bucket_arn}",
                        f"{artifacts_bucket.bucket_arn}/*",
                        f"{artifacts_bucket.bucket_arn}",
                    ],
                ),
                aws_iam.PolicyStatement(
                    actions=["s3:PutObject", "s3:PutObjectAcl"],
                    resources=[
                        f"{raw_bucket.bucket_arn}/*",
                        f"{raw_bucket.bucket_arn}",
                        f"{intermediate_bucket.bucket_arn}/*",
                        f"{intermediate_bucket.bucket_arn}",
                        f"{curated_bucket.bucket_arn}/*",
                        f"{curated_bucket.bucket_arn}",
                        f"{artifacts_bucket.bucket_arn}/*",
                        f"{artifacts_bucket.bucket_arn}",
                    ],
                ),
            ],
        )

        self.raw_bucket = raw_bucket
        self.intermediate_bucket = intermediate_bucket
        self.curated_bucket = curated_bucket
        self.artifacts_bucket = artifacts_bucket
        self.logs_bucket = logs_bucket
        self.readonly_policy = readonly_policy
        self.fullaccess_policy = fullaccess_policy

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
                    "reason": "Resource access restriced for demo resources",
                }
            ),
        ]

        NagSuppressions.add_stack_suppressions(self, suppressions)
