# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

#!/usr/bin/env bash

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
LANGUAGE="unknown"

while [ $# -gt 0 ]
do
    case $1 in
        --language)
        LANGUAGE=${2}
        shift # Remove --language from processing
        shift # Remove $2 from processing
        ;;
        --path)
        FIX_PATH="${DIR}/../${2}"
        shift # Remove --path from processing
        shift # Remove $2 from processing
        ;;
        -*|--*)
        echo "Unknown option $1"
        exit 1
        ;;
    esac
done

cd ${FIX_PATH}
FIX_PATH=`pwd`

echo "Fixing: ${FIX_PATH}, Language: ${LANGUAGE}"

if [[ $LANGUAGE == "python" ]]; then
    echo "Running ruff"
    ruff format ${FIX_PATH}
    ruff check --fix ${FIX_PATH}
elif [[ $LANGUAGE == "typescript" ]]; then
    echo "Running prettier"
    npx prettier --write .
else
    echo "Language: ${LANGUAGE}"
    exit 1
fi