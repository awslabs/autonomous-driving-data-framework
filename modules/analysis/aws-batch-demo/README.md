# AWS Batch Managed demo

## Description

This module:

- deploys an IAM Role assumed by the DAG with permissions to execute the Jobs
- Creates different AWS Batch Compute resources based on the user input
- Creates AWS Batch Queue(s) based on the user input
- Creates 2 sample dags (one gets executed on EC2 and the other on Fargate)

## Inputs/Outputs

### Input Parameters

#### Required

- `dag-bucket-name`: name of the Bucket configured in the shared MWAA Environment to store DAG artifacts
- `dag-path`: name of the path in the Bucket configured in the shared MWAA Environment to store DAG artifacts
- `mwaa-exec-role`: ARN of the MWAA Execution Role
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

- `DagRoleArn`: ARN of the DAG Execution Role created by the Stack
- `OnDemandJobQueueArn`: ARN of the ON_DEMAND AWS Batch Queue
- `SpotJobQueueArn`: ARN of the SPOT AWS Batch Queue
- `FargateJobQueueArn`: ARN of the FARGATE AWS Batch Queue

#### Output Example

```json
{
    "DagRoleArn": "arn::::",
    "OnDemandJobQueueArn": "arn::::",
    "SpotJobQueueArn": "arn::::",
    "FargateJobQueueArn": "arn::::"
}
```
