#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License").
#    You may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import os
import sys

import aws_cdk as cdk
import pytest


@pytest.fixture(scope="function")
def stack_defaults():

    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    if "stack" in sys.modules:
        del sys.modules["stack"]


def test_synthesize_stack(stack_defaults, mocker):
    import stack

    app = cdk.App()
    dep_name = "test-deployment"
    mod_name = "test-module"

    mocker.patch("stack.PythonLayerVersion", return_value=None)
    mocker.patch("stack.PythonFunction", return_value=None)
    try:
        _ = stack.DDBtoOpensearch(
            scope=app,
            id=f"addf-{dep_name}-{mod_name}",
            deployment=dep_name,
            module=mod_name,
            vpc_id="vpc-12345",
            private_subnet_ids='["subnet-00ffc51481090f2d4", "subnet-061322cd815e741e9", "subnet-089eccb47c3d29bf8"]',
            opensearch_sg_id="sg-084c0dd9dc65c6937",
            opensearch_domain_endpoint="vpc-addf-aws-solutions--367e660c-something.us-west-2.es.amazonaws.com",
            opensearch_domain_name="mydomain",
            ddb_stream_arn=(
                "arn:aws:dynamodb:us-west-2:123456789012:table/addf-aws-solutions-metadata-storage-"
                "Rosbag-Scene-Metadata/stream/2023-08-15T03:16:51.909"
            ),
            env=cdk.Environment(
                account=os.environ["CDK_DEFAULT_ACCOUNT"],
                region=os.environ["CDK_DEFAULT_REGION"],
            ),
        )
    except AttributeError:
        pass
