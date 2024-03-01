# ml-training-k8s-managed

This module deploys a Kubernetes Job on Amazon EKS via AWS Step Functions to run sample ML PyTorch training code

## Architecture

The following resources are created:

- Kubernetes Namespace
- Kubernetes ServiceAccount and associated IAM Role
- Kubernetes RBAC Roles and RoleBindings to grant the ServiceAccount access
- Step Functions State Machine definition that calls the EKS RunJob API

The State Machine executes the following steps:

## Parameters

The module requires the following parameters:

- `eks_cluster_name` - Name of the EKS cluster to deploy to 
- `eks_admin_role_arn` - ARN of EKS admin role to authenticate kubectl
- `eks_oidc_provider_arn` - ARN of EKS OIDC provider for IAM roles
- `training_namespace_name` - Kubernetes namespace to create for training

## Output

The module outputs:

- `EksServiceAccountRoleArn` - ARN of the IAM role assigned to the Kubernetes ServiceAccount
- `TrainingNamespaceName` - The Kubernetes namespace created for training
