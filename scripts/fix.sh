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
    echo "Running isort, black"
    isort .
    black .
elif [[ $LANGUAGE == "typescript" ]]; then
    echo "Running prettier"
    npx prettier --write .
else
    echo "Language: ${LANGUAGE}"
    exit 1
fi