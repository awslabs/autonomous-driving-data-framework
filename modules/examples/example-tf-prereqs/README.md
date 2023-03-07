# Terraform Backend Pre-reqs

## Description

This module creates an S3 Bucket and a Dynamo DB Table to fulfill the remote backend and remote state file locking features respectively of terraform

## Inputs/Outputs

### Input Paramenters

Below are the parameters to be declared when instantiating the module

```yaml
name: tf-prereqs
path: modules/examples/example-tf-prereqs/
parameters:
  - name: s3-encryption-type
    value: SSE
  - name: s3-retention-type
    value: RETAIN
  - name: ddb-retention-type
    value: RETAIN
```

#### Optional

- `s3-encryption-type`: the type of encryption on data stored in the buckets
  - `SSE` or `KMS` 
  - Assumed to be `SSE`
- `s3-retention-type`: type of data retention policy when deleting the buckets
  - `DESTROY` or `RETAIN`
  - Assumed to be `DESTROY`
- `ddb-retention-type`: type of data retention policy when deleting the dynamo db table
  - `DESTROY` or `RETAIN`
  - Assumed to be `DESTROY`

### Module Metadata Outputs

- `TfStateBucketName`: Name of the S3 Bucket for storing the remote state file
- `TfLockTable`: Name of the DynamoDB Table Bucket for storing the remote state LockID

#### Output Example

```json
{
  "TfStateBucketName": "addf-tf-s3-bucket-XXX",
  "TfLockTable": "addf-tf-ddb-table-XXX"",
}
```
