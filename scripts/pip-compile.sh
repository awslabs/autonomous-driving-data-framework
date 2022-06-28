#!/usr/bin/env bash
#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#   Licensed under the Apache License, Version 2.0 (the "License").
#   You may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

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

VENV_PATH="${DIR}/venv-$(date +%s)"
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
