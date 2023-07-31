#!/bin/bash 
set -euo pipefail

CDK_VERSION="2.82.0"

while getopts c:m: flag
do
    case "${flag}" in
        c) CDK_VERSION=${OPTARG};;
        m) MODULE_PATH=${OPTARG};;
    esac
done

echo "CDK Version: $CDK_VERSION";
echo "Modules Path: $MODULE_PATH";

npm install -g aws-cdk@${CDK_VERSION}
pip install -r requirements-dev.txt
pip install -r $CODEBUILD_SRC_DIR/modules/$MODULE_PATH/requirements.txt
pytest $CODEBUILD_SRC_DIR/modules/$MODULE_PATH --cov-config=modules/$MODULE_PATH/coverage.ini --cov --cov-report=html:$CODEBUILD_SRC_DIR/reports/$MODULE_PATH/html_dir --cov-report=xml:$CODEBUILD_SRC_DIR/reports/$MODULE_PATH/coverage.xml
