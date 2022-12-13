# Cloud9 Module

## Description

This module creates a Cloud9 instance.  It is not required module.

This module:
- creates a Cloud9 instance
  - Resizes the root volume total storage capacity

##### Please provide `deployspec.yaml` and `modulestack.yaml` files which will be consumed by SeedFarmer CLI.

## Inputs/Outputs

### Input Paramenters

#### Required

- `instance_type`: Type of instance to launch
  - default: t3.small

#### Optional

- `image_id`: The identifier for the Amazon Machine Image (AMI) that's used to create
the EC2 instance. To choose an AMI for the instance, you must specify a
valid AMI alias or a valid AWS Systems Manager path
  - default: ami-0beaa649c482330f7
- `instance_stop_time_minutes`: The number of minutes until the running instance is shut down after the environment was last used
  - default: 60min
- `name`: The name of the environment
- `owner_arn`: The Amazon Resource Name (ARN) of the environment owner. This ARN can be the ARN of any AWS Identity and Access Management principal. If this value is not specified, the ARN defaults to this environment’s creator
  - default: None - however, only the execution role that created the instance will be able to access it
- `storage_size`: The size of the storage of the instance's root volume
    default: 20GB
- `subnet_id`: The ID of the subnet in Amazon Virtual Private Cloud (Amazon VPC) that AWS Cloud9 will use to communicate with the Amazon Elastic Compute Cloud (Amazon EC2) instance
  - default: None

### Module Metadata Outputs

- `Cloud9EnvName`": The name of the Cloud9 instance
- `Cloud9EnvArn`: The arn of the Cloud9 instance
- `InstanceStorageSize`: The size of the storage for the Cloud9 instance,
#### Output Example

```json
{
  "Cloud9EnvName":"cloud9-name","Cloud9EnvArn":"arn:aws:cloud9:us-east-2:000000000:environment:72a3asda1fad4512718114deaad572e",
  "InstanceStorageSize": "20"
}
```
