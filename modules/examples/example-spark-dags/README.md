# Example DAG Module

## Description

This module demonstrates:

- creating a CDK Stack with Role dedicated to the DAGs
  - within the Stack, grant the MWAA Execution Role permission to assume the created DAG Execution Role
- creating DAGs on a shared MWAA Environment by utilizing Input Parameters
  - within the DAG, demonstrate assuming the DAG Execution Role with service and data permissions specific to the DAG
- exporting Metadata by setting the `ADDF_MODULE_METADATA` env var on completion

## Inputs/Outputs

### Input Paramenters

#### Required

- `dag-bucket-name`: name of the Bucket configured in the shared MWAA Environment to store DAG artifacts
- `dag-path`: name of the path in the Bucket configured in the shared MWAA Environment to store DAG artifacts
- `mwaa-exec-role-arn`: ARN of the MWAA Execution Role

#### Optional

- `bucket-policy-arn`: ARN of an IAM Managed Policy to attach to the DAG Execution Role granting access to S3 Data Buckets

### Module Metadata Outputs

- `DagRoleArn`: ARN of the DAG Execution Role created by the Stack

#### Output Example

```json
{
    "DagRoleArn": "arn::::"
}
```
