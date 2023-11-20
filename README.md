# Autonomous Driving Data Framework(ADDF)

<img src="https://github.com/awslabs/autonomous-driving-data-framework/blob/main/docs/images/logo.png?raw=true" width="300" alt="ADDF logo">

ADDF is a collection of modules for Scene Detection, Simulation (mock), Visualization, Compute, Storage, Centralized logging etc, deployed using [SeedFarmer](https://github.com/awslabs/seed-farmer) orchestration tool. ADDF allows you to build distinct, stand alone Infrastructure as code (IAAC) modules and exchange information about dependencies using metadata which can be exported from one module and imported into another. Each module can be found under the `modules` directory of this repository.

## Deployment Instructions

You can refer to the SeedFarmer [guide](https://seed-farmer.readthedocs.io/en/latest) to understand how SeedFarmer CLI can be used to bootstrap and deploy ADDF.

You can follow instructions in the Deployment Guide [Readme](docs/deployment_guide.md). You can also follow the [blogpost](https://aws.amazon.com/blogs/industries/develop-and-deploy-a-customized-workflow-using-autonomous-driving-data-framework-addf-on-aws/) for understanding ADDF in detail.

Please see the [ADDF Security and Operations Guide](https://docs.aws.amazon.com/prescriptive-guidance/latest/addf-security-and-operations/welcome.html) for in-depth recommendations on assessing, deploying, customizing, and operating ADDF.

## Different types of modules supported by ADDF

### Use-case specific Modules

| Type | Description |
| --- | --- |
|  [Rosbag Image Pipeline Module](modules/analysis/rosbag-image-pipeline/README.md)  |  Deploys a Rosbag Image pipeline for use in ADDF  |  
|  [Rosbag WebViz Module](modules/demo-only/rosbag-webviz/README.md) |  Deploys and Visualizes Rosbag Data on AWS using Webviz for use in ADDF  |

### Optional Modules

| Type | Description |
| --- | --- |
|  [DataLake Buckets Module](modules/optionals/datalake-buckets/README.md) |  Deploys shared datalake buckets such as input, intermediate, output, logging, artifact buckets for use in ADDF  |

### Integration Modules

| Type | Description |
| --- | --- |
|  [DDB to Opensearch Module](modules/integration/ddb-to-opensearch/README.md)  |  This module integrates DynamoDB table with Opensearch cluster  |
|  [EKS to Opensearch Module](modules/integration/eks-to-opensearch/README.md) |  This module integrates EKS Cluster with Opensearch cluster  |
|  [EMR to Opensearch Module](modules/integration/emr-to-opensearch/README.md)  |  This module integrates EMR Cluster with Opensearch cluster  |
|  [Opensearch Proxy Module](modules/demo-only/opensearch-proxy/README.md)  |  This module deploys a Proxy server to access Opensearch cluster   |

### Simulation Modules

| Type | Description |
| --- | --- |
|  [K8s-Managed Module](modules/simulations/k8s-managed/README.md)  |  This module helps running simulations on AWS EKS, when triggered by KubernetesJob Operator from airflow environment   |
|  [AWS Batch Module](modules/simulations/batch-managed/README.md) |  This module helps running simulations on AWS Batch, when triggered by Batch Operator from airflow environment  |

### IDE Modules

| Type | Description |
| --- | --- |
|  [Self Managed JupyterHub Module](modules/demo-only/jupyter-hub/README.md)  |  This module deploys self managed JupyterHub environment on AWS EKS  |
|  [Self Managed VSCode Module](modules/demo-only/vscode-on-eks/README.md) |  This module deploys self managed VSCode environment on AWS EKS  |
|  [AWS Managed EMR Studio Module](modules/beta/emrstudio-on-eks/README.md)  |  This module deploys AWS managed EMR Studio with EMR on EKS  |

### Example Modules

| Type | Description |
| --- | --- |
|  [Example DAG Module](modules/examples/example-dags/README.md)  |  This module deploys a pattern to integrate a target DAG module to work with shared MWAA Cluster  |

## Reporting Issues

If you notice a defect, feel free to create an [Issue](https://github.com/awslabs/autonomous-driving-data-framework/issues)

### Deployment FAQ

If you need to debug a deployment in ADDF, here are few things you can checkout [Readme](docs/faq.md)