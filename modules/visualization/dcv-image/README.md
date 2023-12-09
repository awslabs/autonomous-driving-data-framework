# DCV-IMAGE Module

## Description

This module:

- Creates an ECR repo which stores the dcv image.
- Builds the image which will be used as the DCV server.

For the DCV image, it has the following features:
- AmazonLinux2
- NiceDCV server
- Kubernetes Python Client
- AWSCli

## Inputs/Outputs

### Input Paramenters

#### Required

None

#### Optional

- `eks-dcv-repo-name`: a unique name for ECR repo to store dcv image. Default value: `dcv-eks-image`

### Module Metadata Outputs

- `DCVImageRepoUri`: Uri of ECR repo to store dcv image.

#### Output Example

```json
{
    "DCVImageRepoUri":  "arn:aws:ecr:<REGION>:<ACCOUNT_ID>:repository/dcv-eks-image"
}



