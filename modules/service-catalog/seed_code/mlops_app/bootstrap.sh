#!/bin/bash
echo "=================== Installing Dependencies ===================="
# Install system packages

PROJECT_NODE_VERSION=16
sudo yum install wget gcc jq -y

touch $HOME/.bashrc
# Install Nodejs version 16
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.2/install.sh | bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
nvm install $PROJECT_NODE_VERSION
echo $PROJECT_NODE_VERSION >> infra/.nvmrc

# Install CDK Dependencies
nvm use $PROJECT_NODE_VERSION
npm install -g aws-cdk
cd infra
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# Configure git user
echo "======================== .gitignore ========================="
echo "Adding jupyter .gitignore file.."
wget --quiet --no-clobber https://raw.githubusercontent.com/jupyter/notebook/main/.gitignore

echo "Adding cdk .gitignore file..."
cd infra
wget --quiet --no-clobber https://raw.githubusercontent.com/aws-samples/aws-cdk-examples/master/.gitignore
cd ..

echo "======================== Configure GIT ========================="
DEFAULT_GIT_EMAIL=$(git config user.email)
DEFAULT_GIT_USER=$(git config user.name)

read -p "Please enter EMAIL that you want to use for git repository (default \"$DEFAULT_GIT_EMAIL\"): " input_email
GIT_EMAIL="${input_email:-$DEFAULT_GIT_EMAIL}"
git config --local user.email "$GIT_EMAIL"

read -p "Please enter NAME that you want to use for git repository (default \"$DEFAULT_GIT_USER\"): " input_name
GIT_USER="${input_name:-$DEFAULT_GIT_USER}"
git config --local user.name "$GIT_USER"

echo "====================== Configure Project ======================="
SM_PROJECT_NAME=$(cat .sagemaker-code-config | jq -r ".sagemakerProjectName")
read -p "Please enter the use case id (project short-id) (default \"$SM_PROJECT_NAME\"): " input_use_case_id
USE_CASE_ID="${input_use_case_id:-$SM_PROJECT_NAME}"
(cat .sagemaker-code-config | jq ".useCaseId  |= \"${USE_CASE_ID}\"") > .sagemaker-code-config-tmp && mv .sagemaker-code-config-tmp .sagemaker-code-config

PIPELINE_DEFAULT_NAME="$USE_CASE_ID-pipeline"
read -p "Please enter pipeline name that you want to use for the project(default \"$PIPELINE_DEFAULT_NAME\"): " input_pipeline_name
PIPELINE_NAME="${input_pipeline_name:-$PIPELINE_DEFAULT_NAME}"
(cat .sagemaker-code-config | jq ".sagemakerPipelineName  |= \"${PIPELINE_NAME}\"") > .sagemaker-code-config-tmp && mv .sagemaker-code-config-tmp .sagemaker-code-config

echo "Project settings have been saved inside .sagemaker-code-config file. You can later change the pipeline name by editing this file"
echo "=================== .sagemaker-code-config ====================="
(cat .sagemaker-code-config | jq)
echo "======================= Commit Changes ========================="
git add .sagemaker-code-config
git add .gitignore
git add infra/.gitignore
git add infra/.nvmrc
git commit -m "bootstrapped .sagemaker-code-config & .gitignore files"
git push
echo "===================== Bootstrap Complete! ======================"
echo ""
echo "Next run sh deploy.sh to create the infrastructure for this project"