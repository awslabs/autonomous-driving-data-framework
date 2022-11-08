# Example Spark DAG Module

## Description

This module demonstrates a pattern on how to create user specific dag module to run spark jobs by consuming the `emr-on-eks` module from `core` group. The `DagRole` created as a part of the CDK stack declared in this module will be assigned to the airflow run time environment

## Inputs/Outputs

### Input Paramenters

#### Required

- `dag-bucket-name`: name of the Bucket configured in the shared MWAA Environment to store DAG artifacts
- `dag-path`: name of the path in the Bucket configured in the shared MWAA Environment to store DAG artifacts
- `mwaa-exec-role-arn`: ARN of the MWAA Execution Role
- `virtual-cluster-id`: EMR Virtual Cluster ID on which you want to run the spark jobs on
- `emr-job-execution-role-arn`: The Job Execution Role to use for running spark jobs on EMR on EKS
- `raw-bucket-name`: The S3 bucket to download the test dataset and write the results to

### Module Metadata Outputs

- `DagRoleArn`: ARN of the DAG Execution Role created by the Stack

#### Output Example

```json
{
    "DagRoleArn": "arn::::"
}
```
