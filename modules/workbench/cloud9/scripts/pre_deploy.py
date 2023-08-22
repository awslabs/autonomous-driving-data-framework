# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
import time
from typing import Any, Dict, Tuple

import boto3

LOGGING_FORMAT = "[%(asctime)s][%(filename)-13s:%(lineno)3d] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOGGING_FORMAT)
_logger: logging.Logger = logging.getLogger(__name__)

iam_client = boto3.client("iam")

role_name = "AWSCloud9SSMAccessRole"
instance_profile_name = "AWSCloud9SSMInstanceProfile"


def attach_role_to_instance_profile(instance_profile_name: str, role_name: str) -> None:
    try:
        iam_client.add_role_to_instance_profile(InstanceProfileName=instance_profile_name, RoleName=role_name)
    except Exception as err:
        raise err


def check_access_role_exist(role_name: str) -> bool:
    try:
        iam_client.get_role(RoleName=role_name)
        _logger.info(f"Using existing role {role_name}.")
        return True
    except iam_client.exceptions.NoSuchEntityException:
        _logger.warning(f"The role {role_name} does not exist")
        return False


def check_instance_profile_exist(instance_profile_name: str) -> Tuple[bool, Dict[str, Any]]:
    try:
        instance_profile_data = iam_client.get_instance_profile(InstanceProfileName=instance_profile_name)
        _logger.info(f"Using existing instance profile {instance_profile_name}.")
        return (True, instance_profile_data)
    except iam_client.exceptions.NoSuchEntityException:
        _logger.info(f"Instance profile {instance_profile_name} does not exist")
        return (False, {})


def create_access_role(role_name: str) -> None:
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": ["cloud9.amazonaws.com", "ec2.amazonaws.com"]},
                "Action": ["sts:AssumeRole"],
            }
        ],
    }

    try:
        _logger.info(f"Creating role {role_name}")
        iam_client.create_role(
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description="Service linked role for AWS Cloud9",
            Path="/service-role/",
            RoleName=role_name,
            Tags=[
                {"Key": "ADDF_DEPLOYMENT_NAME", "Value": os.getenv("ADDF_DEPLOYMENT_NAME")},
                {"Key": "ADDF_MODULE_NAME", "Value": os.getenv("ADDF_MODULE_NAME")},
            ],
        )
    except Exception as err:
        raise err

    time.sleep(5)

    try:
        _logger.info(f"Attaching policy/AWSCloud9SSMInstanceProfile to {role_name}")
        iam_client.attach_role_policy(
            RoleName=role_name, PolicyArn="arn:aws:iam::aws:policy/AWSCloud9SSMInstanceProfile"
        )
    except Exception as err:
        raise err


def create_instance_profile(instance_profile_name: str) -> None:
    _logger.info(f"Creating instance profile {instance_profile_name}")
    try:
        iam_client.create_instance_profile(
            InstanceProfileName=instance_profile_name,
            Path="/cloud9/",
        )
    except iam_client.exceptions.NoSuchEntityException:
        _logger.warning(f"The role {role_name} does not exist")


if os.getenv("ADDF_PARAMETER_CONNECTION_TYPE") == "CONNECT_SSM":
    if not check_access_role_exist(role_name=role_name):
        create_access_role(role_name=role_name)

    instance_profile_exists, instance_profile_data = check_instance_profile_exist(
        instance_profile_name=instance_profile_name
    )
    if not instance_profile_exists:
        create_instance_profile(instance_profile_name=instance_profile_name)
    else:
        for role in instance_profile_data.get("InstanceProfile", {}).get("Roles", []):
            if role["RoleName"] == role_name:
                break
        else:
            try:
                attach_role_to_instance_profile(instance_profile_name=instance_profile_name, role_name=role_name)
            except Exception as err:
                raise err
