# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import json
import logging
import os
import subprocess
import sys
import typing

import boto3
import kubernetes

NAMESPACE_FILE_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
ADDF_CONFIG_MAP_ENV_VAR_NAME = "DCV_EKS_CONFIG_MAP_NAME"
ADDF_DCV_SESSION_INFO_DISPLAY_KEY = "x11-display"
ADDF_DCV_DISPLAY_KEY_SUFFIX = "display"
ADDF_CONFIG_MAP_PATCH_KEY = "data"
ADDF_DCV_SESSION_NAME = "default-session"
ADDF_SSM_PARAMETER_STORE_ENV_NAME = "DCV_EKS_DISPLAY_PARAMETER_STORE"


def get_display_number() -> str:
    """
    Get the display number from the dcv default-session

    Returns
    -------
    Str
        The display number created by dcv default-session

    Examples
    --------
    >>> get_display_number()
    :0
    """
    ret = subprocess.check_output(["dcv", "describe-session", ADDF_DCV_SESSION_NAME, "--json"]).decode("utf-8")
    session_info = json.loads(ret)

    logging.info(f"Processing session {ADDF_DCV_SESSION_NAME} with info: {session_info}")
    display = str(session_info[ADDF_DCV_SESSION_INFO_DISPLAY_KEY])
    return display


def verify_config_map(
    client_v1: kubernetes.client.api.core_v1_api.CoreV1Api, namespace: str, config_map_name: str
) -> bool:
    """
    Verify the existence of ConfigMap

    Parameters
    ----------
    client_v1: kubernetes.client.api.core_v1_api.CoreV1Api
        Kubernetes client
    namespace: str
        The namespace which the ConfigMap is queried
    config_map_name: str
        The name of the ConfigMap

    Returns
    -------
    bool
        The result of the verification. True for existence and vice versa.

    Examples
    --------
    >>> verify_config_map(client, "dcv", "config-map")
    True
    """
    ret = client_v1.list_namespaced_config_map(namespace)
    for config_map in ret.items:
        if config_map.metadata.name == config_map_name:
            return True
    logging.error(f"Unable to find ConfigMap {config_map_name}")
    return False


def update_config_map(
    client_v1: kubernetes.client.api.core_v1_api.CoreV1Api, namespace: str, config_map_name: str, display: str
) -> bool:
    """
    Update ConfigMap with display number

    Parameters
    ----------
    client_v1: kubernetes.client.api.core_v1_api.CoreV1Api
        Kubernetes client
    namespace: str
        The namespace which the ConfigMap is queried
    config_map_name: str
        The name of the ConfigMap
    display: str
        The display number created by dcv default-session

    Returns
    -------
    bool
        The result of the update. True for successful update in ConfigMap and
        vice
        versa.

    Examples
    --------
    >>> verify_config_map(client, "dcv", "config-map", ":0")
    True
    """
    body: typing.Dict[str, typing.Dict[str, str]] = {ADDF_CONFIG_MAP_PATCH_KEY: {}}

    key = f"{ADDF_DCV_DISPLAY_KEY_SUFFIX}"
    body[ADDF_CONFIG_MAP_PATCH_KEY][key] = display

    config_map_patch_result: typing.Any = client_v1.patch_namespaced_config_map(config_map_name, namespace, body)
    if config_map_patch_result.kind == "ConfigMap":
        return True
    logging.error(f"Unable to update ConfigMap {config_map_name}")
    return False


def update_parameter_store(display: str) -> bool:
    """
    Update ConfigMap with display number

    Parameters
    ----------
    display: str
        The display number created by dcv default-session

    Returns
    -------
    bool
        The result of the update. True for successful updat SSM
        parameters and vice versa.

    Examples
    --------
    >>> update_parameter_store(":0")
    True
    """
    """
    Verify the existence of ConfigMap

    Parameters
    ----------
    client_v1: kubernetes.client.api.core_v1_api.CoreV1Api
        Kubernetes client
    namespace: str
        The namespace which the ConfigMap is queried
    config_map_name: str
        The name of the ConfigMap

    Returns
    -------
    bool
        The result of the verification. True for existence and vice versa.

    Examples
    --------
    >>> verify_config_map()
    True
    """

    client = boto3.client("ssm", region_name=os.getenv("AWS_REGION"))
    try:
        response = client.put_parameter(
            Name=os.getenv(ADDF_SSM_PARAMETER_STORE_ENV_NAME), Value=display, Type="String", Overwrite=True
        )
        logging.info(response)
        return True
    except Exception as e:
        logging.error(e)
        return False


def main() -> None:
    kubernetes.config.load_incluster_config()
    client_v1 = kubernetes.client.CoreV1Api()

    display = get_display_number()

    with open(NAMESPACE_FILE_PATH, "r") as f:
        namespace = f.read()
    logging.info(f"Looking for resource in namespace {namespace}")

    config_map_name = os.getenv(ADDF_CONFIG_MAP_ENV_VAR_NAME, "")
    if config_map_name == "":
        print("ConfigMap name empty")
        sys.exit(1)

    if not verify_config_map(client_v1, namespace, config_map_name):
        sys.exit(1)
    if not update_config_map(client_v1, namespace, config_map_name, display):
        sys.exit(1)
    if not update_parameter_store(display):
        sys.exit(1)


if __name__ == "__main__":
    main()
