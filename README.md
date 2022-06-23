# Autonomous Driving Data Framework(ADDF)

ADDF is a collection of modules for Scene Detection, Simulation (mock), Visualization, Compute, Storage, Centralized logging etc, deployed using [Seed-Farmer](https://github.com/awslabs/seed-farmer) orchestration tool. ADDF allows you to build distinct, stand alone Infrastructure as code (IAAC) modules and exchange information about dependencies using metadata which can be exported from one module and imported into another. Each module can be found under the `modules` directory of this repository.

## Scene Detection

Rosbag Scene Detection Module: Building an automated scene detection pipeline for Autonomous Driving

[Rosbag Scene Detection Module Readme.](modules/analysis/README.md)

## Visualization

Rosbag WebViz Module: Deploy and Visualize ROS Bag Data on AWS using Webviz for Autonomous Driving

[Rosbag WebViz Readme.](modules/demo-only/rosbag-webviz/README.md)

## Shared Core

EKS Compute Module: Deploys shared EKS Cluster with commonly preferred addons for use in ADDF

[EKS Module Readme.](modules/core/eks/README.md)

Metadata Storage Module: Deploys shared Metadata storage module which deploys metadata resources like Glue, DDB etc

[Metadata Storage Module Readme.](modules/core/metadata-storage/README.md)

Amazon Managed Workflows for Apache Airflow (MWAA) Module: Deploys shared MWAA module.

[MWAA Module Readme.](modules/core/mwaa/README.md)

Opensearch Module: Deploys Amazon Opensearch Cluster for use in ADDF

[Opensearch Module Readme.](modules/core/opensearch/README.md)

## Optionals

Networking Module: Deploys standard networking resources such as VPC, Public and Private subnets, endpoints

[Networking Module Readme.](modules/optionals/networking/README.md)

DataLake Buckets Module: Deploys shared datalake buckets such as input, intermediate, output, logging, artifact buckets.

[DataLake Buckets Module Readme.](modules/optionals/datalake-buckets/README.md)

## Deployment Instructions

[Deployment Guide Readme.](docs/deployment_guide.md)

## Support

If you notice a defect, or need support with deployment or demonstrating the kit, create an Issue here: 

### Deployment FAQ (optional)

If you are deploying any of these modulesin a cloud9 environment, the EBS volume used by the environment needs to be resized (increased). Please use this [link]( https://docs.aws.amazon.com/cloud9/latest/user-guide/move-environment.html)
