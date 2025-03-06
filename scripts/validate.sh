# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

#!/usr/bin/env bash

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
    echo "Running ruff"
    ruff format --check ${VALIDATE_PATH}
    ruff check ${VALIDATE_PATH}
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
        echo "Checking mypy"
        mypy .
    fi
    # else
    #     echo "ERROR Language: ${LANGUAGE}"
    #     exit 1
    # fi
fi

if [[ -f ${VALIDATE_PATH}/modulestack.yaml ]]; then
    echo "Checking cfn-lint on modulestack.yaml"
    cfn-lint -i E1029,E3031 --template ${VALIDATE_PATH}/modulestack.yaml
fi
