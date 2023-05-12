"""Helper utilities"""
import json
import logging
import os
from copy import deepcopy
from typing import Dict, List

import boto3
import botocore
import yaml
from deepmerge import always_merger

_logger: logging.Logger = logging.getLogger(__name__)

project_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = "data/eks_dockerimage-replication/versions/"
workload_versions = {}


def _get_ami_version_from_file(eks_version: str) -> str:
    """Get AMI version

    Args:
        eks_version (str): EKS version

    Returns:
        str: AMI version
    """
    _parse_versions_file(eks_version)
    return workload_versions[eks_version]["ami"]["version"]


def _get_chart_release_from_file(eks_version: str, workload_name: str) -> str:
    """Get chart name

    Args:
        eks_version (str): EKS version
        workload_name (str): Workload name

    Returns:
        str: Chart name
    """
    _parse_versions_file(eks_version)
    _parse_versions_file("default")
    if (
        workload_name in workload_versions[eks_version]["charts"]
        and "name" in workload_versions[eks_version]["charts"][workload_name]
    ):
        return workload_versions[eks_version]["charts"][workload_name]["name"]

    return workload_versions["default"]["charts"][workload_name]["name"]


def _get_chart_repo_from_file(eks_version: str, workload_name: str) -> str:
    """Get chart repository URL

    Args:
        eks_version (str): EKS version
        workload_name (str): Workload name

    Returns:
        str: Chart repository URL
    """
    _parse_versions_file(eks_version)
    _parse_versions_file("default")
    if (
        workload_name in workload_versions[eks_version]["charts"]
        and "repository" in workload_versions[eks_version]["charts"][workload_name]
    ):
        return workload_versions[eks_version]["charts"][workload_name]["repository"]

    return workload_versions["default"]["charts"][workload_name]["repository"]


def _get_chart_version_from_file(eks_version: str, workload_name: str) -> str:
    """Get chart version

    Args:
        eks_version (str): EKS version
        workload_name (str): Workload name

    Returns:
        str: Chart version
    """
    _parse_versions_file(eks_version)
    _parse_versions_file("default")
    if (
        workload_name in workload_versions[eks_version]["charts"]
        and "version" in workload_versions[eks_version]["charts"][workload_name]
    ):
        return workload_versions[eks_version]["charts"][workload_name]["version"]

    return workload_versions["default"]["charts"][workload_name]["version"]


def _parse_versions_file(eks_version: str) -> dict:
    """Parse versions file

    Args:
        eks_version (str): EKS version

    Returns:
        dict: Parsed file
    """

    # we do not want to load and parse yaml file for every workload
    if eks_version not in workload_versions:
        yaml_path = os.path.join(data_dir, f"{eks_version}.yaml")

        with open(yaml_path, encoding="utf-8") as yaml_file:
            workload_versions[eks_version] = yaml.safe_load(yaml_file)


def deep_merge(*dicts: Dict) -> Dict:
    """Merges two dictionaries

    Returns:
        Dict: Merged dictionary
    """
    merged = {}
    for d in dicts:
        tmp = deepcopy(d)
        merged = always_merger.merge(merged, tmp)
    return merged


def get_ami_version(eks_version: str) -> str:
    """Get AMI version

    Args:
        eks_version (str): EKS version

    Returns:
        str: AMI version
    """

    return _get_ami_version_from_file(eks_version)


def get_az_from_subnet(subnets: List[str]) -> Dict[str, str]:
    """Get availability zone for subnet

    Args:
        subnets (List[str]): List of subnets

    Returns:
        Dict[str, str]: Correlation between subnet and availability zone
    """
    ec2_client = boto3.client("ec2")
    _logger.info("Subnets info: %s", subnets)
    az_subnet_map = {}
    try:
        response = ec2_client.describe_subnets(SubnetIds=subnets)
        az_subnet_map = {entry["SubnetId"]: entry["AvailabilityZone"] for entry in response["Subnets"]}
    except botocore.exceptions.ClientError as ex:
        _logger.error("Error Describing Subnets: %s", ex)
        if ex.response.get("Error", {}).get("Code", "Unknown") != "InvalidSubnetID.NotFound":
            raise
        else:
            _logger.debug("Exception caught while describing subnets: %s", ex)
    return az_subnet_map


def get_chart_release(eks_version: str, workload_name: str) -> str:
    """Get chart name

    Args:
        eks_version (str): EKS version
        workload_name (str): Workload name

    Returns:
        str: Chart name
    """

    return _get_chart_release_from_file(eks_version, workload_name)


def get_chart_repo(eks_version: str, workload_name: str) -> str:
    """Get chart repository URL

    Args:
        eks_version (str): EKS version
        workload_name (str): Workload name

    Returns:
        str: Chart repository URL
    """

    return _get_chart_repo_from_file(eks_version, workload_name)


def get_chart_values(data: dict, workload_name: str) -> Dict:
    """Get chart additional values

    Args:
        eks_version (str): EKS version
        workload_name (str): Workload name

    Returns:
        Dict: Chart additional values
    """

    if "charts" in data and workload_name in data["charts"] and "values" in data["charts"][workload_name]:
        return data["charts"][workload_name]["values"]

    return {}


def get_chart_version(eks_version: str, workload_name: str) -> str:
    """Get chart version

    Args:
        eks_version (str): EKS version
        workload_name (str): Workload name

    Returns:
        str: Chart version
    """

    return _get_chart_version_from_file(eks_version, workload_name)
