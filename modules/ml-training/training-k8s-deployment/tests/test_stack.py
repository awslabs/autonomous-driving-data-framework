# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import aws_cdk as cdk
import pytest


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    # Unload the app import so that subsequent tests don't reuse

    if "stack" in sys.modules:
        del sys.modules["stack"]


def test_synthesize_stack(stack_defaults):
    import stack

    app = cdk.App()
    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"

    _step_function = stack.TrainingPipeline(
        scope=app,
        id=f"{project_name}-{dep_name}-{mod_name}",
        project_name=project_name,
        deployment_name=dep_name,
        module_name=mod_name,
        eks_cluster_name=mod_name,
        eks_admin_role_arn="arn:aws:iam::123456789012:role/addf-eks-testing-XXXXXX",
        eks_handler_rolearn="arn:aws:iam::123456789012:role/addf-eks-testing-XXXXXX",
        eks_openid_connect_provider_arn="arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/XXXXXXXX",
        eks_cluster_endpoint="oidc.eks.us-west-2.amazonaws.com/id/XXXXXXXXXX",
        eks_cert_auth_data="BQTRJQkR3QXdnZ0VLCkFvSUJ",
        training_namespace_name="namespace",
        training_image_uri="mnist:latest",
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )
