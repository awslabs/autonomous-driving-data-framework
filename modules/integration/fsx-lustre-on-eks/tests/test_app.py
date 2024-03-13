# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import pytest


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["AWS_CODESEEDER_NAME"] = "addf"
    os.environ["ADDF_PROJECT_NAME"] = "test-project"
    os.environ["ADDF_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["ADDF_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
    os.environ["ADDF_EKS_CLUSTER_NAME"] = "cluster"
    os.environ["ADDF_EKS_CLUSTER_ADMIN_ROLE_ARN"] = "arn"
    os.environ["ADDF_EKS_OIDC_ARN"] = "arn"
    os.environ["ADDF_EKS_CLUSTER_SECURITY_GROUP_ID"] = "sfid"
    os.environ["ADDF_FSX_FILE_SYSTEM_ID"] = "fsid"
    os.environ["ADDF_FSX_SECURITY_GROUP_ID"] = "sgid"
    os.environ["ADDF_FSX_MOUNT_NAME"] = "asdf"
    os.environ["ADDF_FSX_DNS_NAME"] = "asfsad"
    os.environ["ADDF_FSX_STORAGE_CAPACITY"] = "1200"
    os.environ["EKS_NAMESPACE"] = "namespace"
    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    with pytest.raises(TypeError):
        import app  # noqa: F401


def test_missing_namespace(stack_defaults):
    del os.environ["EKS_NAMESPACE"]
    with pytest.raises(ValueError):
        import app  # noqa: F401


def test_wrong_capacity(stack_defaults):
    os.environ["SEEDFARMER_FSX_STORAGE_CAPACITY"] = "130"
    with pytest.raises(TypeError):
        import app  # noqa: F401
