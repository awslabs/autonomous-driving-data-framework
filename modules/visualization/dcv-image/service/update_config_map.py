import os
import json
import sys
import subprocess
import logging

from kubernetes import client, config

NAMESPACE_FILE_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
ADDF_CONFIG_MAP_ENV_VAR_NAME = "ADDF_CONFIG_MAP_NAME"
ADDF_APPLICATION_NAMES_ENV_VAR_NAME = "ADDF_APPLICATION_NAMES"
ADDF_DCV_SESSION_INFO_DISPLAY_KEY = "x11-display"
ADDF_DCV_DISPLAY_KEY_SUFFIX = "display"
ADDF_CONFIG_MAP_PATCH_KEY = "data"
ADDF_DCV_SESSION_NAME = "default-session"


def verify_config_map(client_v1, namespace, config_map_name):
    ret = client_v1.list_namespaced_config_map(namespace)
    for config_map in ret.items:
        if config_map.metadata.name == config_map_name:
            return True
    logging.error(f"Unable to find ConfigMap {config_map_name}")
    return False


def update_config_map(client_v1, namespace, config_map_name):
    body = {
        ADDF_CONFIG_MAP_PATCH_KEY: {}
    }
    ret = subprocess.check_output(["dcv", "describe-session", ADDF_DCV_SESSION_NAME, "--json"]).decode('utf-8')
    session_info = json.loads(ret)

    logging.info(f"Processing session {ADDF_DCV_SESSION_NAME} with info: {session_info}")
    display = session_info[ADDF_DCV_SESSION_INFO_DISPLAY_KEY]
    key = f"{ADDF_DCV_DISPLAY_KEY_SUFFIX}"
    body[ADDF_CONFIG_MAP_PATCH_KEY][key] = display

    ret = client_v1.patch_namespaced_config_map(config_map_name, namespace, body)
    if ret.kind == 'ConfigMap':
        return True
    logging.error(f"Unable to update ConfigMap {config_map_name}")
    return False


def main():
    config.load_incluster_config()
    client_v1 = client.CoreV1Api()

    namespace = ""
    with open(NAMESPACE_FILE_PATH, "r") as f:
        namespace = f.read()
    logging.info(f"Looking for resource in namespace {namespace}")

    config_map_name = os.getenv("ADDF_CONFIG_MAP_NAME")

    if not verify_config_map(client_v1, namespace, config_map_name):
        sys.exit(1)
    if not update_config_map(client_v1, namespace, config_map_name):
        sys.exit(1)


if __name__ == '__main__':
    main()
