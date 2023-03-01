# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

=======
## [V1.2.0] - [UNRELEASED]

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
- Added Sagemaker Project support for MLOps

### **Changed**
- modified `core/mwaa` to take a parameterized `requirements.txt` file to support various deployments
- fixed Cloud9 SSM connection type config by creating the underlying resources needed to enable the CDK to deploy
- updated requirements for seed-farmer
- updated `core-eks` module to support install the FSX driver
- existing modules addign `Guidance Solution ID` to the stack
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
