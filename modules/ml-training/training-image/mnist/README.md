# Sample Training Images Module

This module includes sample training Docker Images to demo how training images could be built as a module and integrated into a larger deployment.

## Parameters

The module requires the following parameters:

- `ecr-repository-name` - Name of ECR repository to push built training docker image to
- `ecr-repository-arn` - ARN of ECR repository to push built training docker image to
- `base-image-ecr-account-id` - ECR account ID for the base image
- `base-image-name` - Base image name and tag

## Output

The module outputs:

- `ImageUri` - Image URI (including tag) to use in downstream training pipelines