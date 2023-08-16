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

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
LANGUAGE="python"
SKIP_STATIC_CHECKS="false"

while [ $# -gt 0 ]
do
    case $1 in
        --language)
        LANGUAGE=${2}
        shift # Remove --language from processing
        shift # Remove $2 from processing
        ;;
        --skip-static-checks)
        SKIP_STATIC_CHECKS="true"
        shift # Remove --python from processing
        ;;
        --path)
        VALIDATE_PATH="${DIR}/../${2}"
        shift # Remove --path from processing
        shift # Remove $2 from processing
        ;;
        -*|--*)
        echo "Unknown option $1"
        exit 1
        ;;
    esac
done

cd ${VALIDATE_PATH}
VALIDATE_PATH=`pwd`

echo "Validating: ${VALIDATE_PATH}, Language: ${LANGUAGE}"

echo "Validating Formatting"
if [[ $LANGUAGE == "python" ]]; then
    echo "Checking isort, black"
    isort --check .
    black --check .
elif [[ $LANGUAGE == "typescript" ]]; then
    echo "Checking prettier"
    npx prettier -c .
else
    echo "ERROR Language: ${LANGUAGE}"
    exit 1
fi

if [[ $SKIP_STATIC_CHECKS == "false" ]]; then
    echo "Validating Static Checks"
    if [[ $LANGUAGE == "python" ]]; then
        echo "Checking flake8, mypy"
        flake8 .
        mypy .
    else
        echo "ERROR Language: ${LANGUAGE}"
        exit 1
    fi
fi

if [[ -f ${VALIDATE_PATH}/modulestack.yaml ]]; then
    echo "Checking cfn-lint on modulestack.yaml"
    cfn-lint -i E1029,E3031 --template ${VALIDATE_PATH}/modulestack.yaml
fi
