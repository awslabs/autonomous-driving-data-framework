# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

#!/usr/bin/env bash

# Check if jq is installed...fail if not...
if ! command -v jq &> /dev/null
then
    echo "ERROR:   jq doesn't appear to be installed...please install and rerun this script"
    echo "See https://stedolan.github.io/jq/download/"
    exit 0
fi

## Install the VSCode random password
export VSCODEPWD=$(echo `aws secretsmanager get-random-password --password-length 12 --require-each-included-type  | jq '.RandomPassword'`)
if [[ -z "${VSCODEPWD}" ]]; then
    echo "Error creating vscode credentials, make sure your AWS_DEFAULT_REGION is set and you have proper permissions"
    echo "   "
else
    aws secretsmanager create-secret \
        --name vscode-credentials \
        --description "Credentials for vscode" \
        --secret-string "{\"password\":$VSCODEPWD}"
    echo "vscode-credentials created"
fi

## Install the JupyterHub random password
export JHPWD=$(echo `aws secretsmanager get-random-password --password-length 12 --require-each-included-type  | jq '.RandomPassword'`)
if [[ -z "${JHPWD}" ]]; then
    echo "Error creating jupyterhub credentials, make sure your AWS_DEFAULT_REGION is set and you have proper permissions"
    echo "   "
else
    aws secretsmanager create-secret \
        --name jh-credentials \
        --description "Credentials for jupyterhub" \
        --secret-string "{\"username\":\"testadmin\",\"password\":$JHPWD}"
    echo "jh-credentials created"
fi

## Install the OpenSearch random password
export OSPWD=$(echo `aws secretsmanager get-random-password --password-length 12 --require-each-included-type  | jq '.RandomPassword'`)
if [[ -z "${OSPWD}" ]]; then
    echo "Error creating opensearch credentials, make sure your AWS_DEFAULT_REGION is set and you have proper permissions"
    echo "   "
else
    aws secretsmanager create-secret \
        --name opensearch-proxy-credentials \
        --description "Credentials for opensearch proxy" \
        --secret-string "{\"username\":\"addf\",\"password\":$OSPWD}"
    echo "opensearch-proxy-credentials created"
fi


