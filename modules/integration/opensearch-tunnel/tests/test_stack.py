# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Template


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
    os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
    os.environ["SEEDFARMER_PARAMETER_VPC_ID"] = "vpc-12345"
    os.environ[
        "SEEDFARMER_PARAMETER_OPENSEARCH_DOMAIN_ENDPOINT"
    ] = "vpc-addf-aws-solutions--367e660c-something.us-west-2.es.amazonaws.com"
    os.environ["SEEDFARMER_PARAMETER_OPENSEARCH_SG_ID"] = "sg-084c0dd9dc65c6937"

    if "stack" in sys.modules:
        del sys.modules["stack"]


def test_synthesize_stack(stack_defaults):
    import stack

    app = cdk.App()
    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"

    project_dir = os.path.dirname(os.path.abspath(__file__))
    install_script = os.path.join(project_dir, "..", "install_nginx.sh")

    tunnel = stack.TunnelStack(
        scope=app,
        id=f"{project_name}-{dep_name}-{mod_name}",
        project_name=project_name,
        deployment=dep_name,
        module=mod_name,
        vpc_id="vpc-12345",
        opensearch_sg_id="sg-084c0dd9dc65c6937",
        opensearch_domain_endpoint="vpc-addf-aws-solutions--367e660c-something.us-west-2.es.amazonaws.com",
        install_script=install_script,
        port=3333,
        stack_description="Testing",
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )

    template = Template.from_stack(tunnel)
    template.resource_count_is("AWS::IAM::Role", 1)
    template.resource_count_is("AWS::IAM::InstanceProfile", 1)
    template.resource_count_is("AWS::EC2::Instance", 1)
    template.resource_count_is("AWS::EC2::SecurityGroupIngress", 1)
