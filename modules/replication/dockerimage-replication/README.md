## Introduction

Docker Images replication

### Description

This module helps with replicating Docker images from the list of provided helm charts and any docker image from a public registry into an AWS account's Private ECR. For deploying EKS module or any container related apps in isolated subnets (which has access to AWS APIs via Private endpoints), the respective docker images should be available internally in an ECR repo as a pre-requisiste. This module will generate a `.txt` file which will be populated with list of `to-be-replicated` docker images and the seedfarmer's `deployspec.yaml` invokes the replication.

***CLEANUP***

The cleanup workflow invokes a python script which deletes the replicated docker images from ECR whose prefix starts with `project_name`. This may cause issues if the replicated images are being used by other applications in the same/cross account. The current `deployspec.yaml` doesnt call the python script to cleanup the images, however an end-user can evaluate the need/risk associated and uncomment the relevant instruction under `destroy` phase.

### Input Parameters

#### Required Parameters

- `eks_version`: The EKS Cluster version to lock the version to

#### Required Files

- `dataFiles`: The docker replication module consumes the EKS version specific helm charts inventory to replicate the docker images

#### Manifest Example declaration

```yaml
name: replication
#path: modules/replication/dockerimage-replication/
path: git::https://github.com/awslabs/idf-modules.git//modules/replication/dockerimage-replication?ref=release/1.1.0&depth=1
dataFiles:
  - filePath: data/eks_dockerimage-replication/versions/1.25.yaml
  - filePath: data/eks_dockerimage-replication/versions/default.yaml
parameters:
  - name: eks-version
    value: "1.25"
    # valueFrom:
    #   envVariable: GLOBAL_EKS_VERSION
```

### Module Metadata Outputs

```json
{
    "aws-efs-csi-driver": "1234567890.dkr.ecr.eu-central-1.amazonaws.com/idf-amazon/aws-efs-csi-driver:v1.3.6"
}
```
