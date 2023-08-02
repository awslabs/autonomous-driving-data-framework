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

import pytest


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["ADDF_PROJECT_NAME"] = "test-project"
    os.environ["ADDF_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["ADDF_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
    os.environ[
        "ADDF_PARAMETER_FULL_ACCESS_POLICY_ARN"
    ] = "arn:aws:iam::180024969694:policy/addf-aws-solutions-wip-policy-full-access"
    os.environ["ADDF_PARAMETER_MEMORY_MIB"] = "8192"
    os.environ["ADDF_PARAMETER_PLATFORM"] = "FARGATE"
    os.environ["ADDF_PARAMETER_RETRIES"] = "1"
    os.environ["ADDF_PARAMETER_TIMEOUT_SECONDS"] = "1800"
    os.environ["ADDF_PARAMETER_VCPUS"] = "2"
    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401


def test_missing_app_policy(stack_defaults):
    del os.environ["ADDF_PARAMETER_FULL_ACCESS_POLICY_ARN"]
    with pytest.raises(ValueError):
        import app  # noqa: F401


def test_wrong_platform(stack_defaults):
    del os.environ["ADDF_PARAMETER_PLATFORM"]
    os.environ["ADDF_PARAMETER_PLATFORM"] = "GIBBERISH"
    with pytest.raises(ValueError):
        import app  # noqa: F401
