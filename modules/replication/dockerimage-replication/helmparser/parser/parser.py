"""Parsing utilities"""
import os
from functools import reduce

import yaml

_parsed_file = {}


def _get_branch(data: dict) -> list:
    """Gets branch from the data

    Args:
        data (dict): Dictionary with chart data

    Returns:
        list: Dictionary branches
    """
    branch = data["path"].split(".")

    if "subchart" in data:
        branch = [data["subchart"]] + data["path"].split(".")

    return branch


def _add_branch(tree: dict, branch: list, value: str) -> dict:
    """Adds a branch to a dictionary

    Args:
        tree (dict): Initial dictionary
        branch (list): Dictionary branches
        value (str): Value to add

    Returns:
        dict: _description_
    """
    key = branch[0]
    tree[key] = (
        value
        if len(branch) == 1
        else _add_branch(tree[key] if key in tree else {}, branch[1:], value)
    )
    return tree


def _get_dictionary_value_by_dot_separated_key(dct: dict, key: str) -> str:
    """Gets value from dictionary based on dot-separated key

    Args:
        dct (dict): Dictionary
        key (str): Dot-separated key to find

    Returns:
        str: _description_
    """
    return reduce(lambda c, k: c[k], key.split("."), dct)


def _parse_versions_file(versions_dir: str, eks_version: str) -> dict:
    """Parses versions file

    Args:
        versions_dir (str): Directory with versions files
        eks_version (str): EKS version

    Returns:
        dict: Parsed versions file
    """
    if eks_version not in _parsed_file:
        yaml_path = os.path.join(
            versions_dir,
            f"{eks_version}.yaml",
        )

        with open(yaml_path, encoding="utf-8") as yaml_file:
            _parsed_file[eks_version] = yaml.safe_load(yaml_file)

    return _parsed_file[eks_version]


def _needs_custom_replication(data: dict, image_name: str, type_of_value: str) -> bool:
    """Checks if image needs custom replication

    Args:
        data (dict): Image data
        image_name (str): Image name
        type_of_value (str): Type of value to check for replication

    Returns:
        bool: Boolean value
    """
    if (
        "replication" in data
        and image_name in data["replication"]
        and type_of_value in data["replication"][image_name]
    ):
        return True

    return False


def add_branch_to_dict(dct: dict, data: dict, value: str) -> dict:
    """Adds branch to dictionary

    Args:
        dct (dict): Dictionary
        data (dict): Data about branch
        value (str): Value to add

    Returns:
        dict: Updated dictionary
    """
    branch = _get_branch(data)
    return _add_branch(dct, branch, value)


def get_ami_version(versions_dir: str, eks_version: str) -> str:
    """Gets AMI version from parsed data

    Args:
        versions_dir (str): Directory with versions files
        eks_version (str): EKS version

    Returns:
        str: AMI version string
    """
    workload_versions = _parse_versions_file(versions_dir, eks_version)
    if "ami" in workload_versions and "version" in workload_versions["ami"]:
        return workload_versions["ami"]["version"]

    return ""


def get_workloads(versions_dir: str, eks_version: str) -> dict:
    """Parses versions files

    Args:
        versions_dir (str): Directory with versions files
        eks_version (str): EKS version

    Returns:
        dict: Parsed data
    """
    workload_versions = _parse_versions_file(versions_dir, eks_version)
    workload_data = _parse_versions_file(versions_dir, "default")
    for name, value in workload_versions["charts"].items():
        if "skip" in value and value["skip"]:
            workload_data["charts"].pop(name)
            continue

        if "version" in value:
            workload_data["charts"][name]["version"] = value["version"]

        if "replication" in value:
            workload_data["charts"][name]["replication"] = value["replication"]

    return workload_data["charts"]


def parse_value(
    workload: dict, values: dict, image_name: str, image_data: dict, value_name: str
) -> str:
    """Parses value from the Helm charts based on versions file

    Args:
        workload (dict): Parsed Helm chart
        values (dict): Parsed versions file
        image_name (str): Image name
        image_data (dict): Parsed image data
        value_name (str): Value to search for

    Returns:
        str: Parsed value
    """
    if _needs_custom_replication(values, image_name, value_name):
        return values["replication"][image_name][value_name]

    value = ""
    if "subchart" in image_data:
        value = _get_dictionary_value_by_dot_separated_key(
            workload["subcharts"][image_data["subchart"]][image_data["location"]],
            image_data["path"],
        )
    else:
        value = _get_dictionary_value_by_dot_separated_key(
            workload[image_data["location"]], image_data["path"]
        )

    if "prefix" in image_data:
        value = image_data["prefix"] + value

    return value
