## Introduction

Terraform integration with seedfarmer

## Description

This is a sample implmentation of deploying Terraform IAC using seedfarmer

## Inputs/Outputs

### Input Parameters

Below are the parameters to be declared when instantiating the module

```yaml
name: tf-pattern
path: modules/examples/example-tf/
parameters:
  - name: tf-s3-bucket
    value: "addf-tfstate"
  - name: tf-ddb-table
    value: "addf-tfstate-lock"
```

Below is the pattern to be used when fetching the terraform backend resources from a prereq module.

```yaml
name: tf-pattern
path: modules/examples/example-tf/
parameters:
  - name: tf-s3-bucket
    valueFrom:
      moduleMetadata:
        group: prereqs
        name: tf-prereqs
        key: TfStateBucketName
  - name: tf-ddb-table
    valueFrom:
      moduleMetadata:
        group: prereqs
        name: tf-prereqs
        key: TfLockTable
```

#### Required

- `tf-s3-bucket`: Name of the S3 bucket which Terraform will use to save the remote state. This bucket can be either created externally using enterprise standard infra process or you can instantiate the module `example-tf-prereqs` available under `modules/examples/`
- `tf-ddb-table`: Name of the DynamoDB table which Terraform will use to save the LockID for remote state file locking mechanism. This table can be either created externally using enterprise standard infra process or you can instantiate the module `example-tf-prereqs` available under `modules/examples/`

#### Output Example

```json
{'s3_bucket_id': {'sensitive': False, 'type': 'string', 'value': 'example-XX-us-east-1-XX'}}
```

