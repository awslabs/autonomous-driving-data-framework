# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [V1.1.0] - [Unreleased]

### **Added**

### **Changed**
- modified `metadata-storage` module to create and AWS Event Bridge bus
### **Removed**

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
