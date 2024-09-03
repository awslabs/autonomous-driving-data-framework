# DDB to OpenSearch
## Description

This module deploys an AWS Lambda function in a private subnet to read EMR Cluster's `stderr` logs and write them to
an existing OpenSearch Domain

## Inputs/Outputs

### Input Paramenters

#### Required

- `opensearch-sg-id`: The security group id of the OpenSearch cluster
- `opensearch-domain-endpoint`: The OpenSearch Domain endpoint
- `opensearch-domain-name`: The OpenSearch Domain name
- `vpc-id`: The VPC-ID that the cluster will be created in
- `logs-bucket-name`: The Bucket Name where the EMR logs are configured to be written to(In this case, its shared logs bucket deployed in the `datalake-buckets` module)
- `emr-logs-prefix`: The prefix to which EMR cluster is configured to write logs to

#### Optional

### Module Metadata Outputs

- `LambdaName`: The Lambda Function name which loads the logs from EMR to OpenSearch
- `LambdaArn`: The Lambda Function Arn which loads the logs from EMR to OpenSearch

#### Output Example

```json
{
    "LambdaName":"addf-local-integration-XXXXXXXXX",
    "LambdaArn":"arn:aws:lambda:us-west-2:XXXXXXXXX:function:addf-local-integration-XXXXXXXXX"
}
```
