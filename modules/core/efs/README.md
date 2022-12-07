## Introduction
This module creates an Elastic File System (EFS) service endpoint


## Description

This module will create a new EFS service endpoint and security group tied to the provide VPC.


## Inputs/Outputs


### Input Parameters


#### Required
- `vpc-id` - the VPC ID where this EFS will be tied to via Security Groups
- `removal-policy` - the retention policy to put on the EFS service
  - defaults to `RETAIN`
  - supports `DESTROY` and `RETAIN` only 

#### Optional


#### Input Example
```yaml
  - name: vpc-id
    valueFrom:
      moduleMetadata:
        group: optionals
        name: networking
        key: VpcId
  - name: removal-policy
    value: RETAIN
```


### Module Metadata Outputs

- `EFSFileSystemArn` - the ARN of the EFS
- `EFSFileSystemId` - the unique EFS ID
- `EFSSecurityGroupId` - the created Security Group tied to the EFS
- `VPCId` - the VPC tied to the new EFS

#### Output Example
```json
{
  "EFSFileSystemArn": "arn:aws:elasticfilesystem:us-east-1:12346789012:file-system/fs-0e8893424acfa4722",
  "EFSFileSystemId": "fs-0e8893424acfa4722",
  "EFSSecurityGroupId": "sg-022ccfda45c636da2",
  "VPCId": "vpc-0457f3e6ac3e648c0"
}
```