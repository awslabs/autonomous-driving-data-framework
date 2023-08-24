# AV/ADAS Solution WIP

AV/ADAS Solution

## Table of Contents

## Architecture

The following image shows the architecture of ROSbag image pipeline solution

![ROSbag image pipeline](docs/architecture-1.jpg)

### AWS CDK Constructs

[AWS CDK Solutions Constructs](https://aws.amazon.com/solutions/constructs/) make it easier to consistently create
well-architected applications. All AWS Solutions Constructs are reviewed by AWS and use best practices established by 
the AWS Well-Architected Framework.

## Deployment

You can launch this solution with one click from the AWS Solutions [landing page](REPLACE-ME).

To customize the solution, or to contribute to the solution, see [Creating a custom build](#creating-a-custom-build)

## Configuration

## Creating a custom build

To customize the solution, follow the steps below:

### Prerequisites

The following procedures assumes that all the OS-level configuration has been completed. They are:

* [AWS Command Line Interface](https://aws.amazon.com/cli/)
* [Python](https://www.python.org/) 3.9 or newer
* [AWS CDK](https://aws.amazon.com/cdk/) 2.70.0 or newer

> **Please ensure you test the templates before updating any production deployments.**

### 1. Download or clone this repo

```bash
git clone REPLACE-ME
```

### 2. Create a Python virtual environment for development

```bash
python -m venv .venv 
source ./.venv/bin/activate 
cd ./source 
pip install -r requirements-dev.txt 
```

### 2. After introducing changes, run the unit tests to make sure the customizations don't break existing functionality

```bash
pytest --cov 
```

### 3. Build the solution for deployment

#### Using SeedFarmer Python CLI (recommended)

Packaging and deploying the solution with the AWS CDK allows for the most flexibility in development

```bash
cd ./source/infrastructure 

# set environment variables required by the solution
export BUCKET_NAME="my-bucket-name"

# bootstrap CDK (required once - deploys a CDK bootstrap CloudFormation stack for assets)  
cdk bootstrap --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess

# build the solution 
cdk synth

# build and deploy the solution 
cdk deploy
```

#### Using the solution build tools

It is highly recommended to use the AWS CDK to deploy this solution (using the instructions above). While CDK is used to
develop the solution, to package the solution for release as a CloudFormation template, use the `build-s3-cdk-dist`
build tool: 

```bash
cd ./deployment

export DIST_BUCKET_PREFIX=my-bucket-name  
export SOLUTION_NAME=my-solution-name  
export VERSION=my-version  
export REGION_NAME=my-region

build-s3-cdk-dist deploy \
  --source-bucket-name DIST_BUCKET_PREFIX \
  --solution-name SOLUTION_NAME \
  --version_code VERSION \
  --cdk-app-path ../source/infrastructure/deploy.py \
  --cdk-app-entrypoint deploy:build_app \
  --region REGION_NAME \
  --sync
```

**Parameter Details**
- `$DIST_BUCKET_PREFIX` - The S3 bucket name prefix. A randomized value is recommended. You will need to create an 
  S3 bucket where the name is `<DIST_BUCKET_PREFIX>-<REGION_NAME>`. The solution's CloudFormation template will expect the
  source code to be located in the bucket matching that name.
- `$SOLUTION_NAME` - The name of This solution (example: solution-customization)
- `$VERSION` - The version number to use (example: v0.0.1)
- `$REGION_NAME` - The region name to use (example: us-east-1)

This will result in all global assets being pushed to the `DIST_BUCKET_PREFIX`, and all regional assets being pushed to 
`DIST_BUCKET_PREFIX-<REGION_NAME>`. If your `REGION_NAME` is us-east-1, and the `DIST_BUCKET_PREFIX` is
`my-bucket-name`, ensure that both `my-bucket-name` and `my-bucket-name-us-east-1` exist and are owned by you. 

After running the command, you can deploy the template:

* Get the link of the `SOLUTION_NAME.template` uploaded to your Amazon S3 bucket
* Deploy the solution to your account by launching a new AWS CloudFormation stack using the link of the template above.

> **Note:** `build-s3-cdk-dist` will use your current configured `AWS_REGION` and `AWS_PROFILE`. To set your defaults, install the [AWS Command Line Interface](https://aws.amazon.com/cli/) and run `aws configure`.

> **Note:** You can drop `--sync` from the command to only perform the build and synthesis of the template without uploading to a remote location. This is helpful when testing new changes to the code.

## Collection of operational metrics
This solution collects anonymous operational metrics to help AWS improve the quality of features of the solution.
For more information, including how to disable this capability, please see the [implementation guide](https://docs.aws.amazon.com/prescriptive-guidance/latest/addf-security-and-operations/welcome.html).

***

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License