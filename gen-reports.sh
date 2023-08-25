#!/bin/bash 
set -euo pipefail

CDK_VERSION="2.82.0"
REQUIREMENTS_FILE="requirements.txt"

while getopts c:m:r: flag
do
    case "${flag}" in
        c) CDK_VERSION=${OPTARG};;
        m) MODULE_PATH=${OPTARG};;
        r) REQUIREMENTS_FILE=${OPTARG};;
    esac
done

echo "CDK Version: $CDK_VERSION";
echo "Modules Path: $MODULE_PATH";
echo "Requirements file: $REQUIREMENTS_FILE";

npm install -g aws-cdk@${CDK_VERSION}
pip install -r requirements-dev.txt
pip install -r $CODEBUILD_SRC_DIR/modules/$MODULE_PATH/$REQUIREMENTS_FILE
pytest $CODEBUILD_SRC_DIR/modules/$MODULE_PATH --cov-config=modules/$MODULE_PATH/coverage.ini --cov --cov-report=html:$CODEBUILD_SRC_DIR/reports/$MODULE_PATH/html_dir --cov-report=xml:$CODEBUILD_SRC_DIR/reports/$MODULE_PATH/coverage.xml
