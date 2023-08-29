# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

#!/usr/bin/env bash

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
UPGRADE=""

while [ $# -gt 0 ]
do
    case $1 in
        --path)
        MODULE_PATH="${DIR}/${2}"
        shift # Remove --path from processing
        shift # Remove $2 from processing
        ;;
        --upgrade)
        UPGRADE="--upgrade"
        shift # Remove --upgrade from processing
        ;;
        -*|--*)
        echo "Unknown option $1"
        exit 1
        ;;
    esac
done

if [[ ! -f ${MODULE_PATH}/requirements.in ]]; then
    echo "No requirements.in found in ${MODULE_PATH}"
    exit 1
fi

VENV_PATH="${DIR}/venv-$(date +%s)"
deactivate || echo "No active virtualenv"
python3 -m venv ${VENV_PATH}
. ${VENV_PATH}/bin/activate
echo "Created and activated virtualenv at ${VENV_PATH}"

echo "Installing dependencies from requirements.txt and requirements-dev.txt"
pip install -r ${DIR}/requirements.txt
pip install -r ${DIR}/requirements-dev.txt

echo "Module Path: ${MODULE_PATH}"
pushd ${MODULE_PATH}

if [[ -f requirements.in ]]; then
    echo "Found requirements.in"
    pip-compile ${UPGRADE} requirements.in
fi

echo "Deactivating and removing virtualenv"
popd
deactivate
rm -fr ${VENV_PATH}
