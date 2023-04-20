## Introduction

Docker Images replication

### Description

This module helps with replicating Docker images from the list of provided helm charts into an AWS account's Private ECR. For deploying EKS module or any container related apps in isolated subnets (which has access to AWS APIs via Private endpoints), the respective docker images should be available internally in an ECR repo. This module will generate a `.txt` file which will be populated with docker images and the seedfarmer's `deployspec.yaml` file invokes a shell script to replicate them.

> Note: The cleanup workflow of this module is not working yet. Based on the user's requirements, it will be developed soon

### Input Parameters


#### Required

- `eks_version`: The EKS Cluster version to lock the version to
- `no_replicate`: The flag that disables the replication and only populates the SSM variables with helm chart information

#### Optional

NA

#### Manifest Example declaration

```yaml
parameters:
  - name: eks-version
    valueFrom:
      envVariable: GLOBAL_EKS_VERSION
name: replication
path: modules/replication/dockerimage-replication/
```

### Module Metadata Outputs

```json
{
    "aws-efs-csi-driver": "1234567890.dkr.ecr.eu-central-1.amazonaws.com/addf-amazon/aws-efs-csi-driver:v1.3.6"
}
```
