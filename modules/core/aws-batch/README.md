# AWS Batch Compute Environments and Job Queues

## Description

This module:
- Creates different AWS Batch Compute resources based on the configuration
- Creates AWS Batch Queue(s) based on the user input

## Inputs/Outputs

### Input Parameters

#### Required

- `vpc-id`: The VPC-ID that the cluster will be created in
- `private-subnet-ids`: The Private Subnets that the AWS Batch Compute resources will be deployed to
- `batch-compute`: The Configuration Map for creating AWS Batch Compute environment(s). Below is a sample snippet for providing `batch-compute` input

### Sample declaration of AWS Batch Compute Configuration

```yaml
- name: batch-compute
  value:
    batch_compute_config:
    - env_name: ng1
      compute_type: ON_DEMAND
      max_vcpus: 256
      desired_vcpus: 0
      order: 1
      instance_types: #Example of providing explicit instance type(s)
        - "m5.large"
    - env_name: ng2
      max_vcpus: 256
      desired_vcpus: 0
      compute_type: SPOT
      order: 1
      # instance_types: #if not set, the code defaults to "optimal", where AWS Batch launches the right instance type based on the job definition requirement
      #   - "m5.large"
    - env_name: ng3
      max_vcpus: 256
      desired_vcpus: 0
      compute_type: FARGATE
      order: 1
```

> The above example provides 3 different compute types (ON_DEMAND, SPOT, FARGATE)

#### Optional

### Module Metadata Outputs

- `BatchPolicyString`: Iam Policy for Orchestration Tools like Airflow & Step Functions to Submit Jobs to Batch
- `BatchSecurityGroupId`: Security Group Id of the Batch Compute ECS Cluster
- `OnDemandJobQueueArn`: ARN of the ON_DEMAND AWS Batch Queue
- `SpotJobQueueArn`: ARN of the SPOT AWS Batch Queue
- `FargateJobQueueArn`: ARN of the FARGATE AWS Batch Queue

#### Output Example

```json
{
    "BatchPolicyString": "{iam_policy_doc_string}",
    "BatchSecurityGroupId": "sg-...",
    "OnDemandJobQueueArn": "arn::::",
    "SpotJobQueueArn": "arn::::",
    "FargateJobQueueArn": "arn::::",
}
```
