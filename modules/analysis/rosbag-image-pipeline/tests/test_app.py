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
from json import JSONDecodeError

import pytest


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["ADDF_DEPLOYMENT_NAME"] = "test-project"
    os.environ["ADDF_MODULE_NAME"] = "test-deployment"

    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"

    os.environ["ADDF_PARAMETER_DAG_ID"] = "dag-id"
    os.environ["ADDF_PARAMETER_VPC_ID"] = "vpc-id"
    os.environ["ADDF_PARAMETER_PRIVATE_SUBNET_IDS"] = '["subnet-12345", "subnet-54321"]'
    os.environ["ADDF_PARAMETER_MWAA_EXEC_ROLE"] = "mwaa-exec-role"
    os.environ["ADDF_PARAMETER_FULL_ACCESS_POLICY_ARN"] = "full-access-policy-arn"
    os.environ["ADDF_PARAMETER_SOURCE_BUCKET"] = "source-bucket"
    os.environ["ADDF_PARAMETER_INTERMEDIATE_BUCKET"] = "intermediate-bucket"

    os.environ["ADDF_PARAMETER_ON_DEMAND_JOB_QUEUE_ARN"] = "on-demand-job-queue-arn"
    os.environ["ADDF_PARAMETER_SPOT_JOB_QUEUE_ARN"] = "spot-job-queue-arn"
    os.environ["ADDF_PARAMETER_FARGATE_JOB_QUEUE_ARN"] = "fargate-job-queue-arn"
    os.environ["ADDF_PARAMETER_PARQUET_BATCH_JOB_DEF_ARN"] = "parquet-batch-job-def-arn"
    os.environ["ADDF_PARAMETER_PNG_BATCH_JOB_DEF_ARN"] = "png-batch-job-def-arn"
    os.environ["ADDF_PARAMETER_OBJECT_DETECTION_IMAGE_URI"] = "object-detection-image-uri"
    os.environ["ADDF_PARAMETER_OBJECT_DETECTION_IAM_ROLE"] = "object-detection-iam-role"

    os.environ["ADDF_PARAMETER_LANE_DETECTION_IMAGE_URI"] = "lane-detection-image-uri"
    os.environ["ADDF_PARAMETER_LANE_DETECTION_IAM_ROLE"] = "lane-detection-iam-role"
    os.environ["ADDF_PARAMETER_IMAGE_TOPICS"] = "{}"
    os.environ["ADDF_PARAMETER_SENSOR_TOPICS"] = "{}"

    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401


def test_png_batch_job_def_arn(stack_defaults):
    del os.environ["ADDF_PARAMETER_PNG_BATCH_JOB_DEF_ARN"]

    with pytest.raises(Exception) as e:
        import app  # noqa: F401

        assert "missing input parameter png-batch-job-def-arn" in str(e)


def test_parquet_batch_job_def_arn(stack_defaults):
    del os.environ["ADDF_PARAMETER_PARQUET_BATCH_JOB_DEF_ARN"]

    with pytest.raises(Exception) as e:
        import app  # noqa: F401

        assert "missing input parameter parquet-batch-job-def-arn" in str(e)


def test_object_detection_role(stack_defaults):
    del os.environ["ADDF_PARAMETER_OBJECT_DETECTION_IAM_ROLE"]

    with pytest.raises(Exception) as e:
        import app  # noqa: F401

        assert "missing input parameter object-detection-iam-role" in str(e)


def test_object_detection_image_uri(stack_defaults):
    del os.environ["ADDF_PARAMETER_LANE_DETECTION_IMAGE_URI"]

    with pytest.raises(Exception) as e:
        import app  # noqa: F401

        assert "missing input parameter lane-detection-image-uri" in str(e)


def test_lane_detection_role(stack_defaults):
    del os.environ["ADDF_PARAMETER_LANE_DETECTION_IAM_ROLE"]

    with pytest.raises(Exception) as e:
        import app  # noqa: F401

        assert "missing input parameter lane-detection-iam-role" in str(e)


def test_lane_detection_image_uri(stack_defaults):
    del os.environ["ADDF_PARAMETER_LANE_DETECTION_IMAGE_URI"]

    with pytest.raises(Exception) as e:
        import app  # noqa: F401

        assert "missing input parameter lane-detection-image-uri" in str(e)


def test_vpc_id(stack_defaults):
    del os.environ["ADDF_PARAMETER_VPC_ID"]

    with pytest.raises(Exception) as e:
        import app  # noqa: F401

        assert "missing input parameter vpc-id" in str(e)

def test_private_subnet_ids(stack_defaults):
    del os.environ["ADDF_PARAMETER_PRIVATE_SUBNET_IDS"]

    with pytest.raises(Exception) as e:
        import app  # noqa: F401

        assert "missing input parameter private-subnet-ids" in str(e)

def test_mwaa_exec_role(stack_defaults):
    del os.environ["ADDF_PARAMETER_MWAA_EXEC_ROLE"]

    with pytest.raises(ValueError) as e:
        import app  # noqa: F401

        assert "MWAA Execution Role is missing." in str(e)


def test_full_access_policy(stack_defaults):
    del os.environ["ADDF_PARAMETER_FULL_ACCESS_POLICY_ARN"]

    with pytest.raises(ValueError) as e:
        import app  # noqa: F401

        assert "S3 Full Access Policy ARN is missing." in str(e)


def test_no_queue_provided():
    del os.environ["ADDF_PARAMETER_ON_DEMAND_JOB_QUEUE_ARN"]
    del os.environ["ADDF_PARAMETER_SPOT_JOB_QUEUE_ARN"]
    del os.environ["ADDF_PARAMETER_FARGATE_JOB_QUEUE_ARN"]

    with pytest.raises(ValueError) as e:
        import app  # noqa: F401

        assert "Requires at least one job queue." in str(e)


def test_image_topics_no_json(stack_defaults):
    os.environ["ADDF_PARAMETER_IMAGE_TOPICS"] = "no json"

    with pytest.raises(JSONDecodeError):
        import app  # noqa: F401


def test_sensor_topics_no_json(stack_defaults):
    os.environ["ADDF_PARAMETER_SENSOR_TOPICS"] = "no json"

    with pytest.raises(JSONDecodeError):
        import app  # noqa: F401
