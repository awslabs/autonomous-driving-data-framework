# Custom Kernel Module

## Description

This module builds custom kernel for SageMaker studio from Dockerfile.

## Inputs/Outputs

### Input Paramenters

#### Required

- `custom_kernel_name`: Name of the custom kernel.
- `studio_domain_id`: SageMaker studio domain to attach the kernel to.
- `studio_domain_name`: SageMaker studio name to attach the kernel to.
- `sagemaker_image_name`: Name of the sagemaker image. This variable is also used to find the Dockerfile. The docker build script will be looking for file inside `modules/mlops/custom-kernel/docker/{sagemaker_image_name}`. 1 Dockerfile is added already: `pytorch-10`.

#### Optional

- `app_image_config_name`:  Name of the app image config. Defaults to `addf-{deployment_name}-app-config`
- `kernel_user_uuid`: Default Unix User ID, defaults to: 1000
- `kernel_user_guid`: Default Unix Group ID, defaults to 100
- `kernel_user_mount_path`: # Path to mount in SageMaker Studio, defaults to `/home/sagemaker-user`

### Module Metadata Outputs

- `SageMakerCustomKernelRoleArn`: Role for custom kernel
- `CustomKernelImageName`: Name of the image used for custom kernel
- `AppImageConfigName`: App image config name

#### Output Example

```json
{
    "SageMakerCustomKernelRoleArn": "arn:aws:iam::777013353734:role/addf-shared-infra-kernels-addfsharedinfrakernelske-9O6FZXGI0MM8",
    "CustomKernelImageName": "pytorch-10",
    "AppImageConfigName": "pytorch-10-app-config"
}

```
