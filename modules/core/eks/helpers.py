"""Helper utilities"""
import json
import logging
from copy import deepcopy
from typing import Dict, List

import boto3
import botocore
from deepmerge import always_merger

_logger: logging.Logger = logging.getLogger(__name__)

workload_versions = {}


def _get_ssm_parameter_raw(name: str) -> str:
    """Get SSM parameter as a string

    Args:
        name (str): Name of the SSM parameter

    Returns:
        str: Value of the SSM parameter
    """
    # There are two ways to get SSM parameter using CDK:
    # 1) ssm.StringParameter.value_from_lookup() which pulls parameter during synthesize phase.
    #    Unfortunately, it does not return the actual value, but a dummy value.
    #    There is an issue about this which is closed, but not solved: https://github.com/aws/aws-cdk/issues/8699
    # 2) ssm.StringParameter.value_for_string_parameter() which returns a token: ${Token[TOKEN.723]}
    #    that will be resolved during deployment phase. Unfortunately this is too late, as we need to convert
    #    the data to dictionary before deployment
    # To mitigate this we use boto3

    ssm = boto3.client("ssm")

    try:
        response = ssm.get_parameter(Name=name)
    except botocore.exceptions.ClientError as error:
        if error.response["Error"]["Code"] == "InternalServerError":
            _logger.error("Internal server error")
        elif error.response["Error"]["Code"] == "InvalidKeyId":
            _logger.error("Invalid Key Id")
        elif error.response["Error"]["Code"] == "ParameterNotFound":
            _logger.error("Parameter not found")
        elif error.response["Error"]["Code"] == "ParameterVersionNotFound":
            _logger.error("Parameter version not found")
        raise error

    if "Parameter" in response and "Value" in response["Parameter"]:
        return response["Parameter"]["Value"]

    return ""


def _get_ssm_parameter_as_dict(eks_version: str, workload_name: str) -> Dict:
    """Get SSM parameter and converts it to dictionary

    Args:
        eks_version (str): EKS version
        workload_name (str): Workload name

    Returns:
        Dict: Parsed SSM parameter
    """
    response = _get_ssm_parameter_raw(f"/addf/eks/chart/{workload_name}-{eks_version}")

    if response:
        return json.loads(response)

    return {}


def get_ami_version(eks_version: str) -> str:
    """Get AMI version

    Args:
        eks_version (str): EKS version

    Returns:
        str: AMI version
    """
    return _get_ssm_parameter_raw(f"/addf/eks/ami/{eks_version}")


def get_chart_repo(eks_version: str, workload_name: str) -> str:
    """Get chart repository URL

    Args:
        eks_version (str): EKS version
        workload_name (str): Workload name

    Returns:
        str: Chart repository URL
    """
    if workload_name not in workload_versions:
        workload_versions[workload_name] = _get_ssm_parameter_as_dict(eks_version, workload_name)

    if "helm" in workload_versions[workload_name] and "repository" in workload_versions[workload_name]["helm"]:
        return workload_versions[workload_name]["helm"]["repository"]

    return ""


def get_chart_release(eks_version: str, workload_name: str) -> str:
    """Get chart name

    Args:
        eks_version (str): EKS version
        workload_name (str): Workload name

    Returns:
        str: Chart name
    """
    if workload_name not in workload_versions:
        workload_versions[workload_name] = _get_ssm_parameter_as_dict(eks_version, workload_name)

    if "helm" in workload_versions[workload_name] and "name" in workload_versions[workload_name]["helm"]:
        return workload_versions[workload_name]["helm"]["name"]

    return ""


def get_chart_version(eks_version: str, workload_name: str) -> str:
    """Get chart version

    Args:
        eks_version (str): EKS version
        workload_name (str): Workload name

    Returns:
        str: Chart version
    """
    if workload_name not in workload_versions:
        workload_versions[workload_name] = _get_ssm_parameter_as_dict(eks_version, workload_name)

    if "helm" in workload_versions[workload_name] and "version" in workload_versions[workload_name]["helm"]:
        return workload_versions[workload_name]["helm"]["version"]

    return ""


def get_chart_values(eks_version: str, workload_name: str) -> Dict:
    """Get chart additional valuess

    Args:
        eks_version (str): EKS version
        workload_name (str): Workload name

    Returns:
        Dict: Chart additional values
    """
    if workload_name not in workload_versions:
        workload_versions[workload_name] = _get_ssm_parameter_as_dict(eks_version, workload_name)

    if "values" in workload_versions[workload_name]:
        return workload_versions[workload_name]["values"]

    return {}


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
