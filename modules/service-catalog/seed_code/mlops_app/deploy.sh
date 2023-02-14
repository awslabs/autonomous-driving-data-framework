#!/bin/bash

# infrastructre should be deployed from infra directory
cd infra && source $PWD/source-activate-venv
# deploy cdk app. This action will ask for approval
cdk deploy --app "python app.py"
# this needs to be run only once.
# After that, all changes will be picked up directly from repository main branch
