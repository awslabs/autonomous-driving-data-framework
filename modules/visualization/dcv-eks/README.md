
# DCV-EKS Module

## Description

This module creates necessary resources for DCV server to work.
- Updates EKS node role to include permissions to access DCV license in S3
- Updates security groups of the nodes to allow ingress traffic (TCP and UDP) to specific DCV nodeport
- Creates a role for DCV pods to access AWSSecretsManager and kubernetes resources
- Creates necessay k8s resources:
  - Role: for DCV pods to manage specific k8s resources
  - ServiceAccount: for DCV pods to assume IAM role and k8s role
  - RoleBinding: to bind k8s role to the k8s service account
  - ConfigMap: to store dcv runtime output, such as `display` and `socket_path` which application pods will be using to render applications
  - Service: NodePort service to open port on each node and forward traffic locally to the DCV pod
  - DaemonSet: daemonset for dcv containers which also include failure handling

## Deployment
### Prerequisites
- AWS SecretsManager entries for username `dcv-cred-user` and password `dcv-cred-passwd` already established

#### Using AWS SecretsManager
The key `dcv-cred-user` and `dcv-cred-passwd` need to exist in AWS SecretsManager.

## Inputs/Outputs

### Input Paramenters

#### Required

None

#### Optional
- `DCVImageRepoUri` - repo arn which stores DCV image.
- `EksClusterAdminRoleArn` - the role which creates the eks cluster
- `EksClusterName` - the name of the EKS cluster
- `EksOidcArn` - full ARN of the OIDC provider
- `EksClusterOpenIdConnectIssuer` - OIDC provider URI
- `EksClusterSecurityGroupId` - id of security group which is attached to all nodes in eks
- `EksNodeRoleArn` - arn of the role which is attached to all nodes in eks
- `DcvNamespace`: the namespace to store all DCV related resources. Defaults to `dcv`.
- `DcvNodePort`: the nodeport which will be used by nodeport service. Defaults to `31980`.

### Module Metadata Outputs

- `DcvEksRoleArn`: arn of the role 
- `DcvNamespace`: the namespace to create all DCV resources
- `DcvNodeport`: port number of the DCV Nodeport service

#### Output Example

```json
{
    "DcvEksRoleArn": "arn:aws:iam::XXXXXXXX:role/DcvEksRole",
    "DcvNamespace": "dcv",
    "DcvNodeport": 31980
}



