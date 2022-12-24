# Amazon EMR Serverless

## Description

This module:

- creates an Amazon EMR Serverless Application
- creates an IAM Role and policy for Jobs on the EMR Application

## Inputs/Outputs

### Input Paramenters

#### Required

- None

#### Optional

- None
 
### Module Metadata Outputs

- `EmrApplicationId`: name of the S3 Bucket configured to store MWAA Environment DAG artifacts
- `EmrJobExecutionRoleArn`: name of the path in the S3 Bucket configured to store MWAA Environment DAG artifacts

#### Output Example

```json
{
    "EmrApplicationId": "application id",
    "EmrJobExecutionRoleArn": "arn:::::"
}
```
