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
    os.environ["CDK_DEFAULT_ACCOUNT"] = "12345678"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-2"
    os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_ADMIN_ROLE_ARN"] = (
        "arn:aws:iam:us-east-1:1234567890:role/test-role"
    )
    os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_NAME"] = "test_cluster"
    os.environ["SEEDFARMER_PARAMETER_EKS_OIDC_ARN"] = (
        "arn:aws:eks:us-east-1:1234567890:oidc-provider/oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/test-ocid"
    )
    os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_OPEN_ID_CONNECT_ISSUER"] = (
        "test_open_id_connect_issuer"
    )
    os.environ["SEEDFARMER_PARAMETER_APPLICATION_ECR_URI"] = (
        "1234567890.dkr.ecr.us-east-1.amazonaws.com/test-repo"
    )
    os.environ["SEEDFARMER_PARAMETER_SQS_NAME"] = "test-message-queue"
    os.environ["SEEDFARMER_PARAMETER_FSX_VOLUME_HANDLE"] = "fs-12345678"
    os.environ["SEEDFARMER_PARAMETER_FSX_MOUNT_POINT"] = "mnttest"
    os.environ["SEEDFARMER_PARAMETER_DATA_BUCKET_NAME"] = "test-data-bucket"

    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401


def test_project_deployment_name_length(stack_defaults):
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project-incredibly"

    with pytest.raises(Exception) as e:
        import app  # noqa: F401
    assert (
        "module cannot support a project+deployment name character length greater than"
        in str(e)
    )
