# Datalake Buckets

## Description

This module creates buckets and policies to support a datalake. 

This module:

- creates buckets to support a datalake
  - Raw Data Bucket
  - Intermediate Data Bucket
  - Curated Data Bucket
  - Logs Data Bucket
  - Artifact Data Bucket
- creates access policies for the buckets
  - READ-ONLY
  - FULL ACCESS

##### Please provide `deployspec.yaml` and `modulestack.yaml` files which will be consumed by SeedFarmer CLI.

## Inputs/Outputs

### Input Paramenters

#### Required

None

#### Optional

- `encryption-type`: the type of encryption on data stored in the buckets
  - `SSE` or `KMS` 
  - Assumed to be `SSE`
- `retention-type`: type of data retention policy when deleteing the buckets
  - `DESTROY` or `RETAIN`
  - Assumed to be `DESTROY`


### Module Metadata Outputs

- `RawBucketName`: name of the bucket housing the raw data input
- `CuratedBucketName`: name of the bucket housing the data after processing
- `IntermediateBucketName`: name of the bucket housing data as it is in process
- `ArtifactsBucketName`: name of the bucket housing artifacts used for processing
- `LogsBucketName`: name of the bucket housing logs
- `ReadOnlyPolicyArn`: ARN of the policy generated giving read-only access to content
- `FullAccessPolicyArn`: ARN of the policy generated giving full access to content

#### Output Example

```json
{
  "ArtifactsBucketName": "addf-dep-artifacts-bucket-us-east-1-12345678901",
  "CuratedBucketName": "addf-dep-curated-bucket-us-east-1-123456789012",
  "FullAccessPolicyArn": "arn:aws:iam::123456789012:policy/addf-dep-optionals-datalake-buckets-us-east-1-123456789012-full-access",
  "IntermediateBucketName": "addf-dep-intermediate-bucket-us-east-1-123456789012",
  "LogsBucketName": "addf-dep-logs-bucket-us-east-1-123456789012",
  "RawBucketName": "addf-dep-raw-bucket-us-east-1-123456789012",
  "ReadOnlyPolicyArn": "arn:aws:iam::123456789012:policy/addf-dep-optionals-datalake-buckets-us-east-1-123456789012-readonly-access"
}
```
