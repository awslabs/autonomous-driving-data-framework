# Amazon EMR Serverless

## Description

This module:

- creates an Amazon EMR Serverless Application
- creates an IAM Role and policy for Jobs on the EMR Application

## Inputs/Outputs

### Input Paramenters

#### Required

- `vpc-id`: The VPC-ID that the cluster will be created in
- `private-subnet-ids`: The Private Subnets that the AWS Batch Compute resources will be deployed to

#### Optional

- `solution-id`: a unique identifier for this deployment (must be used with `solution-description`)
- `solution-name`: a unique name for this deployment (must be used with `solution-id`)
- `solution-version`: a unique version for this deployment

The parameters `(solution-*)` will resolve a custom text that is used as a description of the stack if populated. 
### Module Metadata Outputs

- `EmrApplicationId`: name of the S3 Bucket configured to store MWAA Environment DAG artifacts
- `EmrJobExecutionRoleArn`: name of the path in the S3 Bucket configured to store MWAA Environment DAG artifacts

#### Output Example

```json
{
    "EmrApplicationId": "application id",
    "EmrJobExecutionRoleArn": "arn:::::"
}