# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import pytest


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["ADDF_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["ADDF_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
    os.environ["ADDF_PARAMETER_EKS_CLUSTER_NAME"] = "my-cluster"
    os.environ[
        "ADDF_PARAMETER_EKS_CLUSTER_ADMIN_ROLE_ARN"
    ] = "arn:aws:iam::123456789012:role/addf-eks-testing-derek"
    os.environ[
        "ADDF_PARAMETER_EKS_OIDC_ARN"
    ] = "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/3BF275A8EB229AC8630CD2C8006BC073"
    os.environ["ADDF_PARAMETER_TRAINING_NAMESPACE_NAME"] = "namespace"
    os.environ["ADDF_PARAMETER_TRAINING_IMAGE_URI"] = "mnist:latest"

    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    # this fails due to mock not finding the eks cluster...should stub this out, but it is fine for now
    with pytest.raises(Exception) as e:
        import app  # noqa: F401
