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
    os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_NAME"] = "cluster"
    os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_ADMIN_ROLE_ARN"] = "arn:aws:iam:::role/x"
    os.environ["SEEDFARMER_PARAMETER_EKS_OIDC_ARN"] = "arn:aws:eks:::oidc-provider/y"
    os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_SECURITY_GROUP_ID"] = "sfid"
    os.environ["SEEDFARMER_PARAMETER_FSX_FILE_SYSTEM_ID"] = "fsid"
    os.environ["SEEDFARMER_PARAMETER_FSX_SECURITY_GROUP_ID"] = "sgid"
    os.environ["SEEDFARMER_PARAMETER_FSX_MOUNT_NAME"] = "asdf"
    os.environ["SEEDFARMER_PARAMETER_FSX_DNS_NAME"] = "asfsad"
    os.environ["SEEDFARMER_PARAMETER_FSX_STORAGE_CAPACITY"] = "1200"
    os.environ["EKS_NAMESPACE"] = "namespace"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401


def test_missing_namespace(stack_defaults):
    del os.environ["EKS_NAMESPACE"]
    with pytest.raises(ValueError):
        import app  # noqa: F401


def test_wrong_capacity(stack_defaults):
    os.environ["SEEDFARMER_PARAMETER_FSX_STORAGE_CAPACITY"] = "130"
    with pytest.raises(ValueError):
        import app  # noqa: F401
