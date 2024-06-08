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
    project_name = "test-project"
    deployment_name = "test-deployment"
    module_name = "test-module"

    metadata_storage_stack = stack.MetadataStorageStack(
        scope=app,
        id=f"{project_name}-{deployment_name}-{module_name}",
        project_name=project_name,
        deployment_name=deployment_name,
        module_name=module_name,
        scene_table_suffix="scene-suffix",
        bagfile_table_suffix="glue-db-suffix",
        glue_db_suffix="ros-table-suffix",
        stack_description="Testing",
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )

    template = Template.from_stack(metadata_storage_stack)
    template.resource_count_is("AWS::DynamoDB::Table", 2)
    template.resource_count_is("AWS::Glue::Database", 1)
