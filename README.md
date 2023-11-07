# Scene Intelligence with Rosbag on AWS

Scene Intelligence with Rosbag on AWS - Solution

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

### 1. Download/clone this repo and checkout the branch of interest

```bash
git clone https://github.com/awslabs/autonomous-driving-data-framework.git
cd autonomous-driving-data-framework/
git checkout scene-intelligence-with-rosbag-on-aws
```

### 2. Create a Python virtual environment for development

```bash
python -m venv .venv 
source ./.venv/bin/activate 
cd ./source 
pip install -r requirements-dev.txt 
```

### 3. Customize the solution

Please refer to the [customization guide](https://docs.aws.amazon.com/solutions/latest/scene-intelligence-with-rosbag-on-aws/customization-guide.html) available in the implementation guide

## Collection of operational metrics

This solution collects anonymous operational metrics to help AWS improve the quality of features of the solution.
For more information, including how to disable this capability, please see the [implementation guide](https://docs.aws.amazon.com/solutions/latest/scene-intelligence-with-rosbag-on-aws/).

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
