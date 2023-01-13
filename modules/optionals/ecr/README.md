# ECR Module

## Description

This module creates elastic container registry.

## Inputs/Outputs

### Input Paramenters

#### Required

None

#### Optional

- `repository_name`: Repository name. Defaults to `addf-{module_name}-ecr-repository`
- `image_tag_mutability`: Image tag mutability. Defaults to `"IMMUTABLE"`. Possible values: `"IMMUTABLE"` or `"MUTABLE"`
- `lifecycle_max_days`: Max days to store the images in ECR. Defaults to `None`, (no removal of images)
- `lifecycle_max_image_count`: Max images to store the images in ECR. Defaults to `None`, (no removal of images)


### Module Metadata Outputs

- `RepositoryName`: ECR repository name
- `RepositoryARN`: ECR repository ARN



#### Output Example

```json
{
    "RepositoryName": "pytorch-10",
    "RepositoryARN": "arn:aws:ecr:<REGION>:<ACCOUNT_ID>:repository/pytorch-10"
    }

```
