# Kubernetes Managed Simulation

## Description

This module:

- deploys an ECR repository and pushes a docker container from images/pytorch-mnist for the training job

- deploys an IAM Role assumed by the DAG with permissions to execute the Jobs
- deploys a k8s `namespace` dedicated to simulations
- deploys an IAM Role and associated k8s ServiceAccount that Jobs will use for execution
- deploys a Step Function to execute the pytorch image on kubernetes

## Inputs/Outputs

### Input Parameters

#### Required

- `eks-cluster-name`: name of the EKS Cluster to send Jobs to
- `eks-oidc-arn`: ARN of the OpenID Connect Provider assigned to the EKS Cluster
- `eks-cluster-admin-role-arn`: ARN of the IAM Role configured as a Cluster Admin and associated with the `system:masters` Kubernetes Group


### Module Metadata Outputs

- `EksServiceAccountRoleArn`: ARN of the EKS Role used by the Step Function to orchestrate the training job

#### Output Example

```json
{
    "EksServiceAccountRoleArn": "arn::::"
}
```
