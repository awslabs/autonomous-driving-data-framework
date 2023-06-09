# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

=======

## Patch Changes - [06/07/2023]
### **Changed**
Due to the removal of support for node 12.x in AWS Lambda, a number of modules using AWS-CDK were upgraded from 2.20.0 to 2.82.0.  This branch is a DIRECT copy of `release/1.0.0-reinvent` with the changes to the CDK as indicated:
- modules/optionals/datalake-buckets
- modules/core/opensearch
- modules/demo-only/rosbag-webviz
- modules/analysis/rosbag-scene-detection

The following modules had their Lambda Layers requirements.txt modified:
- modules/integration/ddb-to-opensearch (layer/requirements.txt)
- modules/integration/emr-to-opensearch (layer/requirements.txt)

Updated the YoloV5 container for Object Detection (modules/post-processing/yolo-object-detection)
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
