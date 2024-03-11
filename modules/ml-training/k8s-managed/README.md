# ml-training-k8s-managed

This module deploys a Kubernetes Job on Amazon EKS via AWS Step Functions to run sample ML PyTorch training code

## Architecture

The following resources are created:

- Kubernetes Namespace
- Kubernetes ServiceAccount and associated IAM Role
- Kubernetes RBAC Roles and RoleBindings to grant the ServiceAccount access
- Step Functions State Machine definition that calls the EKS RunJob API

The State Machine executes the following steps:
1. Execute EKS Job on the target cluster in the training-namespace
2. Retrieve Raw Logs

## Parameters

The module requires the following parameters:

- `eks-cluster-name` - Name of the EKS cluster to deploy to 
- `eks-admin-role-arn` - ARN of EKS admin role to authenticate kubectl
- `eks-oidc-provider-arn` - ARN of EKS OIDC provider for IAM roles
- `training-namespace-name` - Kubernetes namespace to create for training
- `training-image-uri` - Docker Image URI to use for training

## Output

The module outputs:

- `EksServiceAccountRoleArn` - ARN of the IAM role assigned to the Kubernetes ServiceAccount
- `TrainingNamespaceName` - The Kubernetes namespace created for training
