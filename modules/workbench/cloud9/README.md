# Cloud9 Module

## Description

This module creates a Cloud9 instance and the option to resize the root volume

## Inputs/Outputs

### Input Paramenters

#### Required

- `image_id`: The identifier for the Amazon Machine Image (AMI) that's used to create the EC2 instance. To choose an AMI for the instance, you must specify a valid AMI alias or a valid AWS Systems Manager path
  - e.g.: ami-0beaa649c482330f7
- `instance_type`: Type of instance to launch
  - e.g.: t3.small. For more information on instance types: https://aws.amazon.com/ec2/instance-types/
- `owner_arn`: The Amazon Resource Name (ARN) of the environment owner. This ARN can be the ARN of any AWS Identity and Access Management principal.
    If this value is not specified, the ARN defaults to this environment’s creator. This role should be the user you use to get access to your AWS account. For example,
    if you are using Federated access, the `owner_arn` would look similar to this: `arn:aws:iam::0123456789:assumed-role/Admin/userName`
- `subnet_id`: The ID of the subnet in Amazon Virtual Private Cloud (Amazon VPC) that AWS Cloud9 will use to communicate with the Amazon Elastic Compute Cloud (Amazon EC2) instance

#### Optional

- `connection_type`: The connection type used for connecting to an Amazon EC2 environment. Valid values are `CONNECT_SSM` and `CONNECT_SSH`
  - default: CONNECT_SSM
- `instance_name`: The name of the Cloud9 environment
- `instance_stop_time_minutes`: The number of minutes until the running instance is shut down after the environment was last used
  - default: 60min
- `storage_size`: The size of the storage of the instance's root volume
    default: 20GB

### Module Metadata Outputs

- `Cloud9EnvName`": The name of the Cloud9 instance
- `Cloud9EnvArn`: The arn of the Cloud9 instance
- `InstanceStorageSize`: The size of the storage for the Cloud9 instance

#### Output Example

```json
{
  "Cloud9EnvName":"cloud9-name",
  "Cloud9EnvArn":"arn:aws:cloud9:us-east-2:000000000:environment:72a3asda1fad4512718114deaad572e",
  "InstanceStorageSize": "20"
}
```
