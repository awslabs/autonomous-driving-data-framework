# Kubernetes Managed Simulation

## Description

This module:

- deploys an ECR repository and pushes a docker container from images/pytorch-mnist for the training job

- deploys an IAM Role assumed by the DAG with permissions to execute the Jobs
- deploys a k8s `namespace` dedicated to simulations
- deploys an IAM Role and associated k8s ServiceAccount that Jobs will use for execution
- deploys Airflow DAGs to the shared MWAA that execute k8s Jobs to mock simulations
  - `simple_mock` DAG: uses a simple `bash` script to sleep for a random amount of time and randomly fail the conatainer
  - `coarse_parallel_mock` DAG: uses an SQS Queue to orchestrate a mock Coarse Parallel Processing workflow, where each Pod takes a message off the queue, processes it, then exits
  - `fine_parallel_mock` DAG: uses an an SQS Queue to orchestrat a mock Fine Parallel Processing workflow, where each Pod continuously processes messages off the queue until it is empty, then exits

## Inputs/Outputs

### Input Parameters

#### Required

- `dag-bucket-name`: name of the Bucket configured in the shared MWAA Environment to store DAG artifacts
- `dag-path`: name of the path in the Bucket configured in the shared MWAA Environment to store DAG artifacts
- `mwaa-exec-role-arn`: ARN of the MWAA Execution Role
- `eks-cluster-name`: name of the EKS Cluster to send Jobs to
- `eks-cluster-kubectl-role-arn`: ARN of the IAM Role used to execute `kubectl` commands on the EKS Cluster
- `eks-oidc-arn`: ARN of the OpenID Connect Provider assigned to the EKS Cluster
- `eks-cluster-admin-role-arn`: ARN of the IAM Role configured as a Cluster Admin and associated with the `system:masters` Kubernetes Group


### Module Metadata Outputs

- `DagRoleArn`: ARN of the DAG Execution Role created by the Stack
- `

#### Output Example

```json
{
    "DagRoleArn": "arn::::",
    "EksServiceAccountRoleArn": "arn::::"
}
```
