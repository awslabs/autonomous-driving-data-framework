# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import aws_cdk as cdk
import pytest


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
    os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    if "stack" in sys.modules:
        del sys.modules["stack"]


def test_synthesize_stack(stack_defaults):
    import stack_fsx_eks

    app = cdk.App()
    proj_name = "addf"
    dep_name = "test-deployment"
    mod_name = "test-module"

    stack_fsx_eks.FSXFileStorageOnEKS(
        scope=app,
        id=f"{proj_name}-{dep_name}-{mod_name}",
        project_name=proj_name,
        deployment_name=dep_name,
        module_name=mod_name,
        eks_cluster_name="myekscluster",
        eks_admin_role_arn="arn:aws:iam::123456789012:role/eks-admin-role",
        eks_oidc_arn="arn:aws:iam::123456789012:oidc-provider/server.example.com",
        eks_cluster_security_group_id="sg-0123456",
        fsx_file_system_id="foobar",
        fsx_security_group_id="sg-0123456",
        fsx_mount_name="foobar",
        fsx_dns_name="example.com",
        fsx_storage_capacity="1200Gi",
        eks_namespace="service.example.com",
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )
