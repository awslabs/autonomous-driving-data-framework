# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import pytest


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["ADDF_DEPLOYMENT_NAME"] = "test-proj"
    os.environ["ADDF_MODULE_NAME"] = "test-dep"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
    os.environ["ADDF_PARAMETER_ROSBAG_SCENE_TABLE_SUFFIX"] = "scene-suffix"
    os.environ["ADDF_PARAMETER_GLUE_DB_SUFFIX"] = "glue-db-suffix"
    os.environ["ADDF_PARAMETER_ROSBAG_BAGFILE_TABLE_SUFFIX"] = "ros-table-suffix"

    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401


def test_scene_suffix(stack_defaults):
    del os.environ["ADDF_PARAMETER_ROSBAG_SCENE_TABLE_SUFFIX"]

    with pytest.raises(Exception):
        import app  # noqa: F401

        assert os.environ["ADDF_PARAMETER_ROSBAG_SCENE_TABLE_SUFFIX"] == "scene-suffix"


def test_glue_db_suffix(stack_defaults):
    del os.environ["ADDF_PARAMETER_GLUE_DB_SUFFIX"]

    with pytest.raises(Exception):
        import app  # noqa: F401

        assert os.environ["ADDF_PARAMETER_GLUE_DB_SUFFIX"] == "glue-db-suffix"


def test_bagfile_suffix(stack_defaults):
    del os.environ["ADDF_PARAMETER_ROSBAG_BAGFILE_TABLE_SUFFIX"]

    with pytest.raises(Exception):
        import app  # noqa: F401

        assert os.environ["ADDF_PARAMETER_ROSBAG_BAGFILE_TABLE_SUFFIX"] == "ros-table-suffix"
