# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

#!/usr/bin/env bash

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"


FIX_PATH="${DIR}/../${1}"

cd ${FIX_PATH}
FIX_PATH=`pwd`

echo "Path: ${FIX_PATH}"

source ${FIX_PATH}/prep-cdk-nag.sh
echo "Env prepped"
cdk synth --app "python ${FIX_PATH}/app.py"