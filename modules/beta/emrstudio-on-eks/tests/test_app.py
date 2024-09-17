# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os
import sys
from unittest import mock

import pytest


@pytest.fixture(scope="function", autouse=True)
def stack_defaults():
    with mock.patch.dict(os.environ, {}, clear=True):
        os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
        os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
        os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"

        os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
        os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

        os.environ["SEEDFARMER_PARAMETER_VPC_ID"] = "vpc-123"
        os.environ["SEEDFARMER_PARAMETER_PRIVATE_SUBNET_IDS"] = json.dumps(["subnet-123", "subnet-456"])

        os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_NAME"] = "test-cluster"
        os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_ADMIN_ROLE_ARN"] = "arn:aws:iam::111111111111:role/test-role"
        os.environ["SEEDFARMER_PARAMETER_EKS_OIDC_ARN"] = (
            "arn:aws:iam::111111111111:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/XXXXXX"
        )
        os.environ["SEEDFARMER_PARAMETER_EKS_OPENID_ISSUER"] = "oidc.eks.us-east-1.amazonaws.com/id/XXXXXX"
        os.environ["SEEDFARMER_PARAMETER_ARTIFACT_BUCKET_NAME"] = "test-bucket"
        os.environ["SEEDFARMER_PARAMETER_SSO_USERNAME"] = "sso-username"

        # Unload the app import so that subsequent tests don't reuse
        if "app" in sys.modules:
            del sys.modules["app"]

        yield


def test_app(stack_defaults):
    import app  # noqa: F401
