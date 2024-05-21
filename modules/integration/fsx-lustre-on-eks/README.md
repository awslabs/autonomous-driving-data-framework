## Introduction
This module creates an FSx service endpoint integration with an existing EKS cluster.  The FSx endpoint should already be deployed
with an atttached Security Group in the same VPC as the EKS cluster.  We do not support VPC-Peering at this time. 


## Description


## Inputs/Outputs


### Input Parameters


#### Required
- `eks-cluster-admin-role-arn` - the role that has kubectl access / admin access to the EKS clsuter
- `eks-cluster-name` - the name of the EKS cluster
- `eks-oidc-arn` - the OpenID provider ARN of the cluster
- `eks-cluster-security-group-id` - the EKS cluster security group to allow ingress to FSX
- `fsx-file-system-id` - the FSX ID
- `fsx-security-group-id` - the Security Group ID that is tied to FSX
- `fsx-mount-name` - the mount name of the FSX service
- `fsx-dns-name` - the dns name tied to the FSX service
- `namespace` - the namespace that the PVC will be created in - a string value
  - only one of `namespace`, `namespace_ssm` or `namespace_secret` can be used 
- `namespace_ssm` - the name of the SSM parameter that has the string value to be used as the Namespace that the PVC will be created in
  - only one of `namespace`, `namespace_ssm` or `namespace_secret` can be used 
- `namespace_secret` - the name of the SSM parameter that has the string value to be used as the Namespace that the PVC will be created in
  - only one of `namespace`, `namespace_ssm` or `namespace_secret` can be used 
  - if using this parameter, the unique entry to AWS SecretsManager is required with the following JSON format (username representing the namespace):
    ```json
    {
      "username": "user1"
    }
    ```

#### Optional
- `fsx-storage-capacity`: the amount (in GB) of storage, **defaults to 1200**, with the following guidelines:
  -  valid values are 1200, 2400 , and increments of 3600

#### Input Example
```yaml
parameters:
  - name: EksClusterAdminRoleArn
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterAdminRoleArn
  - name: EksClusterName
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterName
  - name: EksOidcArn
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksOidcArn
  - name: EksClusterSecurityGroupId
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterSecurityGroupId
  # - name: NamespaceSsm
  #   valueFrom:
  #     parameterStore:  lustrenamespace
  # - name: NamespaceSecret
  #   value: addf-dataservice-users-kubeflow-users-kf-testing
  - name: Namespace
    value: usernamespace
  - name: FsxFileSystemId
    value: fs-066f18902985xxxxx
  - name: FsxSecurityGroupId
    value: sg-0559ec713631xxxxx
  - name: FsxMountName
    value: k5z2tbev
  - name: FsxDnsName
    value: fs-066f18902985fdba0.fsx.us-east-1.amazonaws.com
```

### Module Metadata Outputs
- `Namespace` - the namespace the Persistent Volume Claim is created in EKS
- `PersistentVolumeClaimName` - the name of the Persistent Volume Claim as it appears in EKS
- `PersistentVolumeName` - the name of the Persistent Volume as it appears in EKS
- `StorageClassName` - the name of the storage class as it appears in EKS

#### Output Example
```json
{
  "Namespace": "dgraeber",
  "PersistentVolumeClaimName": "test-lustre-eks-fsx-pvc",
  "PersistentVolumeName": "test-lustre-eks-fsx-pv",
  "StorageClassName": "test-lustre-eks-fsx-sc"
}

```