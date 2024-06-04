# DCV-EKS Module

## Description

<TODO: Rewrite this to be up to date>

## Deployment

### Prerequisites

- AWS SecretsManager secret `dcv-credentials` with UserName and Password already established (as described in the dcv-image module)

#### Using AWS SecretsManager

The secret `dcv-credentials` needs to exist with key `UserName` and `Password` keys.

## Inputs/Outputs

### Input Paramenters

#### Required

- `dcv-image-uri` - DCV container image uri
- `eks-cluster-admin-role-arn` - the role which creates the eks cluster
- `eks-handler-role-arn` - The IAM role of EKS Cluster handler for running kubectl commands
- `eks-cluster-name` - the name of the EKS cluster
- `eks-oidc-arn` - full ARN of the OIDC provider
- `eks-cluster-open-id-connect-issuer` - OIDC provider URI
- `eks-cluster-security-group-id` - id of security group which is attached to all nodes in eks
- `eks-node-role-arn` - arn of the role which is attached to all nodes in eks

#### Optional

- `dcv-namespace`: the namespace to store all DCV related resources. Defaults to `dcv`.

### Module Metadata Outputs

- `DcvEksRoleArn`: arn of the role
- `DcvNamespace`: the namespace to create all DCV resources

- `DcvDisplayParameterName`: SSM parameter name for display number
- `DcvSocketMountPathParameterName`: SSM parameter name for shared directory path in worker node

#### Output Example

```json
{
    "DcvEksRoleArn": "arn:aws:iam::XXXXXXXX:role/DcvEksRole",
    "DcvNamespace": "dcv",
    "DcvDisplayParameterName": "/addf/mlops/dcv-eks-dcv-eks/dcv-display",
    "DcvSocketMountPathParameterName": "/addf/mlops/dcv-eks-dcv-eks/dcv-socket-mount-path"
}


## Additional Resources

- https://docs.aws.amazon.com/dcv/latest/adminguide/setting-up-installing-linux-prereq.html
- https://github.com/cazlo/aws-batch-using-nice-dcv/blob/el9/README.md


