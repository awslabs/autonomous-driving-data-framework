# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

=======

## UNRELEASED

### **Added**

### **Changed**

- updating cdk version for rosbag-webviz module, keeping in sync with release/1.0.0-reinvent branch
- Fixed a bug in the ECR module to capture the metadata
- Refactor to use ecr module from idf
- updated `typing-extensions~=4.6.3` in modules that were below that spec to support seed-farmer 3.1.x
- fixed security updates about apache-airflow version
- made os-tunnel module generic by importing seedfarmer project name

### **Removed**

=======

## [V3.0.0] - [11/09/2023]

### **Added**

- adding new `integration/opensearch-tunnel` module
- Added unit-tests, enabled logging and versioning on buckets for datalake-buckets module
- Added Unit tests to metadata-storage module
- Added new `dcv-image` and `dcv-eks` module

### **Changed**

- Improve the existing example-tf module to demonstrate how to use terraform.tfvars file and establish the wiring between root variables.tf, module level variables.tf and vars/terraform.tfvars per env
- Refactored YOLOP Lane detection module
- Refactored Rosbag Image pipeline module to include scene detection workflow in the DAG and standardized inputs consumption from external modules
- Added manifest files supporting AV/ADAS as AWS-Solutions
- updating `sensor-extraction/ros-to-parquet` with license and tests 
- Deprecated rosbag-scene-detection module in favor of rosbag-image-pipeline module
- changed license-headers on non-av/adas solution modules
- updating `post-processing/yolop-lane-detection` with license and tests
- updating `post-processing/yolo-object-detection` with license and tests
- syncing `integration/opensearch-tunnel` module
- CDK version change, changed license-headers on datalake-buckets module
- CDK Version change, sonar checks improvements and changed license-headers on metadata-storage module
- upgraded CDK version, changed the license-headers, deployed sagemaker jobs inside VPC sonar code improvements on rosbag-image-pipeline module
- updating `sensor-extraction/ros-to-png` with license and tests 
- Deprecated rosbag-scene-detection module in favor of rosbag-image-pipeline module
- changed license-headers on non-av/adas solution modules
- updating `integration/ddb-to-opensearch` with license and tests
- reducing nested layer complexity of the `ddb-to-opensearch` lambda as per code-smell checks
- updating `certifi>=2023.7.22` for requirements-dev.* on the following modules
  - analysis/aws-batch-demo
  - analysis/rosbag-image-pipeline
  - integration/efs-on-eks
  - mlops/kuebflow-platform
  - mlops/kubeflow-users
  - post-processing/lane-detection
  - post-processing/yolo-object-detection
  - post-processing/yolop-lane-detetion
  - sensor-extraction/ros-to-png
  - sensor-extraction/ros-to-parquet
  - simulations/batch-managed
  - simulations/k8s-managed
- Refactored Rosbag Image pipeline module to work with mwaa 2.6.3
- fixed the dependabot alerts (apache-airflow)
- refactored pyspark script of scene-detect in rosbag-image-processing module
- `datalake-buckets` has LifecycleRule on `artifacts-bucket-logs` added due to number of MWAA access logs
- updated `Pillow~=10.0.1` in modules/analysis/rosbag-image-pipeline/requirements-dev.txt
- added dynamic stack naming based on Solution Info:
  -  modules/optionals/datalake-buckets
  -  modules/analysis/rosbag-image-pipeline
  -  modules/core/metadata-storage
  -  modules/sensor-extraction/ros-to-parquet
  -  modules/sensor-extraction/ros-to-png
  -  modules/post-processing/yolo-object-detection
  -  modules/post-processing/yolop-lane-detection
  -  modules/integration/opensearch-tunnel
  -  modules/integration/ddb-to-opensearch
- updated `rosbag-webviz` cdk version to 2.99.1
- added solution info to boto calls on dag of `rosbag-image-pipeline`
- updating emr-launch version to 2.0.1 in `rosbag-scene-detection`
- standardized ecr module outputs
- updated `kubeflow-users` module to match support for kf1.7
- updated `kubeflow-platform` manifest to use matching kf to eks 1.25 as example
### **Removed**

- removed `aws-batch-demo` module since its no longer used for demos
- removed `setup.py`files for sensor extraction and labelling modules

=======

## [V2.0.0] - [06/28/2023]

- Adding unit-tests layout
- integration with custom CIDR of eks for grabbing IPs from extended VPC CIDR
- being able to launch EKS module separately with no external module dependency
- being able to launch EKS module in isolated subnets by replicating docker images beforehand
- started sourcing k8s plugin/apps versions w/ eks versions from yaml files - dataDir
- integration with calico for network level isolation
- integration with kyverno for implementing gov policy as code for k8s
- Added detailed guide on how to launch EKS cluster in private and isolated subnets
- Added Amazon EKS add-ons ADOT which is a secure, production-ready, AWS supported distribution of the OpenTelemetry project.

### **Changed**

- updating seed-farmer version
- the way node groups are built by accepting only single instancetypes per asg, encrypting the disks at rest
- integration with custom CIDR of eks for grabbing IPs from extended VPC CIDR
- the helm chart values, registries and repo info being loaded from versions files than being hardcoded locally for EKS module
- updated the manifests files to use `gitpath` and source modules/files from IDF

### **Removed**

- removing `requirements-dev.txt` for FSx-Lustre module
- removing MWAA dependencies to `requirements-dev.txt` in analysis, sensor-extraction, simulations modules
- removed modules: networking from `optionals` group, efs, fsx-lustre, aws-batch, eks, neptune, opensearch, mwaa from `core` group and `dockerimages-replication` from `replication` group as they have been replicated to IDF

=======
## [V1.2.1] - [6/7/2023]

### **Added**


### **Changed**
Due to the removal of support for node 12.x in AWS Lambda, a number of modules using AWS-CDK were upgraded from 2.20.0 to 2.82.0.  This branch is a DIRECT copy of `release/1.2.0` with the changes to the CDK as indicated:
- modules/optionals/datalake-buckets
- modules/core/eks
- modules/core/opensearch
- modules/demo-only/rosbag-webviz
- modules/analysis/rosbag-scene-detection
- modules/integration/eks-to-opensearch
- modules/simulations/k8s-managed

The following modules had their Lambda Layers requirements.txt modified:
- modules/integration/ddb-to-opensearch (layer/requirements.txt)
- modules/integration/emr-to-opensearch (layer/requirements.txt)
  
- updated the YoloV5 container for Object Detection (modules/post-processing/yolo-object-detection)
- updated emrstudio module cdk
- updated vscode cdk version and leveraged alb controller already on eks cluster
- added helm install to kf-platform

### **Removed**
- the following branches have been deprecated:
  - release/1.0.0
  - release/0.1.0
  - release/1.1.0
  - release/1.2.0

=======

## [V1.2.0] - [3/20/2023]

### **Added**

- Cloud9 module
- Added Visualization Instance Deployment to the ros-image-demo manifest
- Added `sagemaker/sagemaker-studio` module: Deploy's SageMaker Studio, including user Management and auto-stop lifecycle hooks
- Added `sagemaker/custom-kernel` module: Registers, builds and pushes custom-kernel and SageMaker Processing/Training Images
- Added `service-catalog` module: Allows creating Service Catalog Products and Portfolios, including custom SageMaker Project Organizational Templates from Seed Code. The module also includes a sample project that deploys full MLOPs solution with extendable CDK code inside of Studio.
- Added `optionals/ecr` module: Creates Elastic Container Registry repositories with CDK
- Added SageMaker `manifests/mlops-sagemaker` manifests: Deploys the ECR, SageMaker Studio, Service Catalog and Custom SageMaker Project Template together
- FSx on Lustre module
- FSx-Lustre support on EKS (`integration/fsx-lustre-on-eks`)
- Added a sample demo module to deploy Terraform IAC using seedfarmer
- Added a prereq module to deploy terraform backend resources
- Added Sagemaker Project support for MLOps

### **Changed**

- modified `core/mwaa` to take a parameterized `requirements.txt` file to support various deployments
- fixed Cloud9 SSM connection type config by creating the underlying resources needed to enable the CDK to deploy
- updated requirements for seed-farmer
- updated `core-eks` module to support install the FSX driver
- existing modules addign `Guidance Solution ID` to the stack
- Updated seedfarmer version from `2.4.0` to `2.5.0`
- Refactored Networking module to create isolated subnets added to the existing public/private subnets

### **Removed**

- removed `"ts-jest": "^29.0.3"` from `demo-only/rosbag-webviz/package.json` due to lib conflicts (introduced bu dependabot)


=======
## [V1.1.0] - [12/19/2022]

### **Added**

- Added node label support to core eks module 
- Added version support for core eks module with additional alb version mappings by default
- Added a pattern for Event bridge triggering StepFunctions triggering AWS Batch
- Added a module to support the execution of Spark Jobs on AWS EMR on EKS.
- Added an example spark dags module to demonstrate how to consume `emr-on-eks` module for running spark jobs on AWS EMR on EKS
- Added EFS support as a core module
- Addded EFS-on-EKS as an integration module to create a Storage Class
- Added Kubeflow-on-AWS support via `mlops/kubeflow-platform` module
- Added Kubeflow-on-AWS USERS support via `mlops/kubeflow-users` module
- Wireframes for UI - see https://github.com/awslabs/autonomous-driving-data-framework/tree/feature/webapp-wireframes/WebApp/Wireframes
- added support for Data visualization (Camera, Radar, CAN bus, Map) with NICE DCV and Foxglove
### **Changed**

- changing removal policy of EFS to `RETAIN` by default in core-eks module
- Added a pattern for Event bridge triggering StepFunctions triggering AWS Batch
- Added support for configurable EBS Volumes in AWS Batch module, to enable working with larger datasets 
- Modified the CNI Helper role name and on  eks module 
- Ros to Png Image Extraction relies on EC2 capacity providers in AWS Batch instead of Fargate
- Updated default accountId resolution in sample manifests to simple key:value mapping to reduce confusion
- Updated `seedfarmer` version to 2.2.1 for being able to use `.env` files
- in `modules/analysis/rosbag-scene-detection` limited the length of the name of the `StepFunctionTrigger` 
### **Removed**

=======
## [V1.0.0] - [09/27/2022]

### **Added**

- updated docs with the information about deploying addf with seedfarmer 2.0v which enables multi region and multi account deployments
- aws-batch-demo pipeline and manifest
- image extraction (rosbag to png) pipeline with yolov5 object detection
- sensor extraction (rosbag to parquet) added to image pipeline
- added docker module to build container images
- added lane detection module for building docker image into ECR
- object and lane detection added to the rosbag-image-pipeline
- added lane detection WITH YOLOP module for building docker image into ECR
- replace lanedet with yolop for lane detection pipeline

### **Changed**

- fixed the missing modules info in readme
- added details to the contributing guide
- modifed text in modules/analysis/rosbag-scene-detection
- enforce HTTPS on OpenSearch
- EFS FileSystemPolicies to improve security
- removed all referneces to secrestsmanager in modulestack.yaml where not needed
- core/eks module added region modifier to masterrole references

### **Removed**

## [V0.1.0]

- Initial Release
