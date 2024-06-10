# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import pytest


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
    os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
    os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_NAME"] = "my-cluster"
    os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_ADMIN_ROLE_ARN"] = (
        "arn:aws:iam::123456789012:role/eks-testing-XXXXXX"
    )
    os.environ["SEEDFARMER_PARAMETER_EKS_OIDC_ARN"] = (
        "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/XXXXXXXX"
    )
    os.environ["SEEDFARMER_PARAMETER_TRAINING_NAMESPACE_NAME"] = "namespace"
    os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_ENDPOINT"] = (
        "oidc.eks.us-west-2.amazonaws.com/id/XXXXXXXXXX"
    )
    os.environ["SEEDFARMER_PARAMETER_EKS_CERT_AUTH_DATA"] = "BQTRJQkR3QXdnZ0VLCkFvSUJ"
    os.environ["SEEDFARMER_PARAMETER_TRAINING_IMAGE_URI"] = "mnist:latest"

    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401


def test_cluster_name(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_NAME"]

    with pytest.raises(Exception):
        import app  # noqa: F401

        assert os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_NAME"] == "my-cluster"


def test_training_namespace_name(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_TRAINING_NAMESPACE_NAME"]

    with pytest.raises(Exception):
        import app  # noqa: F401

        assert os.environ["SEEDFARMER_PARAMETER_TRAINING_NAMESPACE_NAME"] == "namespace"


def test_cert_auth_data(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_EKS_CERT_AUTH_DATA"]

    with pytest.raises(Exception):
        import app  # noqa: F401

        assert (
            os.environ["SEEDFARMER_PARAMETER_EKS_CERT_AUTH_DATA"]
            == "BQTRJQkR3QXdnZ0VLCkFvSUJ"
        )
