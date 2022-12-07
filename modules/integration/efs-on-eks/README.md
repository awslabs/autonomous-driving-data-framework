## Introduction
This module creates an Elastic File System (EFS) service endpoint integration with an existing EKS cluster.


## Description
This module will take an existing EFS with a Security group, an existing EKS cluster (in VPC) and deploy a Storage Class for EFS on EKS.
It creates ingress allowances for the EKS cluster via the Security Groups.

## Inputs/Outputs


### Input Parameters


#### Required
- `eks-cluster-admin-role-arn` - the role that has kubectl access / admin access to the EKS clsuter
- `eks-cluster-name` - the name of the EKS cluster
- `eks-oidc-arn` - the OpenID provider ARN of the cluster
- `eks-cluster-security-group-id` - the EKS cluster security group to allow ingress to the EFS
- `efs-file-system-id` - the EFS ID
- `efs-security-group-id` - the Security Group ID that is tied to the EFS
- `vpc-id` - the VPC ID where the Secrity Groups reside

#### Optional
NONE

#### Input Example
```yaml
parameters:
  - name: eks-cluster-admin-role-arn
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterAdminRoleArn
  - name: eks-cluster-name
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterName
  - name: eks-oidc-arn
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksOidcArn
  - name: eks-cluster-security-group-id
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterSecurityGroupId
  - name: efs-file-system-id
    valueFrom:
      moduleMetadata:
        group: efs
        name: efs
        key: EFSFileSystemId
  - name: efs-security-group-id
    valueFrom:
      moduleMetadata:
        group: efs
        name: efs
        key: EFSSecurityGroupId
  - name: vpc-id
    valueFrom:
      moduleMetadata:
        group: efs
        name: efs
        key: VpcId
```

### Module Metadata Outputs
- `EFSStorageClassName` - the name of the storage class as it appears in EKS
- `EKSClusterName` - a reference to the cluster where this storage class is deployed

#### Output Example
```json
{
  "EFSStorageClassName": "efs-eks-efs-efs",
  "EKSClusterName": "addf-mlops-core-eks-cluster"
}

```