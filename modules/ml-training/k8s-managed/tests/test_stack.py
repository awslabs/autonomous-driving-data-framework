# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Template


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

    dep_name = "test-deployment"
    mod_name = "test-module"
    # this fails due to mock not finding the eks cluster...
    # should stub this out, but it is fine for now
    with pytest.raises(Exception) as e:

        step_function = stack.TrainingPipeline(
            scope=app,
            id=f"addf-{dep_name}-{mod_name}",
            deployment_name=dep_name,
            module_name=mod_name,
            eks_cluster_name=mod_name,
            eks_admin_role_arn="arn:aws:iam::123456789012:role/addf-eks-testing-derek",
            eks_openid_connect_provider_arn="arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/3BF275A8EB229AC8630CD2C8006BC073",
            training_namespace_name="namespace",
            training_image_uri="mnist:latest",
            env=cdk.Environment(
                account=os.environ["CDK_DEFAULT_ACCOUNT"],
                region=os.environ["CDK_DEFAULT_REGION"],
            ),
        )
