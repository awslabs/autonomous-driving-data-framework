# Amazon Managed Workflows for Apache Airflow (MWAA)

## Description

This module:

- creates an MWSS Environment to execute DAGs created by other modules
- creates an IAM Role (the MWAA Execution Role) with least privilege permissions
- *Optionally* creates an S3 Bucket to store DAG artifacts

## Inputs/Outputs

### Input Paramenters

#### Required

- `vpc-id`: VPC Id where the MWAA Environment will be deployed
- `private-subnet-ids`: List of Private Subnets Ids where the MWAA Environment will be deployed

#### Optional

- `dag-bucket-name`: name of the S3 Bucket to configure the MWAA Environment to monitor for DAG artifacts. An S3 Bucket is created if none is provided
- `dag-path`: path in the S3 Bucket to configure the MWAA Environment to monitor for DAG artifacts. Defaults to `dags` if none is provided
- `environment-class`: the MWAA Environement Instance Class. Defaults to `mw1.small` if none is provided
- `max-workers`: the Maximum number of workers to configure the MWAA Environment to allow. Defaults to `25` if none is provided
- `airflow-version`: The Airflow version you would want to set in the module. It is defaulted to `2.2.2`

### Module Metadata Outputs

- `DagBucketName`: name of the S3 Bucket configured to store MWAA Environment DAG artifacts
- `DagPath`: name of the path in the S3 Bucket configured to store MWAA Environment DAG artifacts
- `MwaaExecRoleArn`: ARN of the MWAA Execution Role created by the Stack

#### Output Example

```json
{
    "DagBucketName": "some-bucket",
    "DagPath": "dags",
    "MwaaExecRoleArn": "arn:::::"
}
```
