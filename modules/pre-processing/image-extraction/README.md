# Pre Processing workflow

## Description

This module contains a Docker container for extracting images/frames from a JSQ and IDX file combination. In the context of AM/ADAS we want to extract images stored in a file. We have 2 access pattern one that would linearly extract all images and another one which would only extract a portion of those images. Here, you could use the metadata from the recording such as GPS track, CAN signals to identify part of the recording that would require further investigation avoiding extracting the entire recording.

This module mounts datasets using `Mountpoint for Amazon S3` and enables extraction of images without having to download them locally.

## Inputs/Outputs

### Input Parameters

#### Required

- `vpc-id`: VPC Id to be used by the Pre Processing resources.
- `private-subnet-ids`: List of Private Subnets Ids where the Pre Processing resources should be deployed to.
- `artifact-bucket-name`: The Artifact bucket to which Scene Detection pipeline can upload any assets, other than module specific data.
- `ecr-repo-name`: ECR Repository name to be used/created if it doesnt exist.
- `on-demand-job-queue-arn`: Job Queue ARN from Batch Compute Core Module.

#### Optional

- `timeout-seconds`: AWS Batch job container execution timeout value.

### Sample declaration

```yaml
name: image-extraction
path: modules/pre-processing/image-extraction
parameters:
  - name: artifacts-bucket-name
    valueFrom:
      moduleMetadata:
        group: optionals
        name: buckets
        key: ArtifactsBucketName
  - name: ecr-repo-name
    value: image-extraction-image-repo
  - name: on-demand-job-queue-arn
    valueFrom:
      moduleMetadata:
        group: core
        name: batch-compute
        key: OnDemandJobQueueArn
  - name: timeout-seconds
    value: 2000
  # - name: start-range
  #   value: 0
  # - name: end-range
  #   value: 100
```

### Module Metadata Outputs

- `ImageExtractionDkrImageUri`: AWS ECR URI of the container image
- `BatchExecutionRoleArn`: ARN of the IAM Role for running the AWS Batch container

#### Output Example

```json
{
  "BatchExecutionRoleArn": "arn:aws:iam::123456789012:role/addf-123456789012",
  "ImageExtractionDkrImageUri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/image-extraction-image-repo:latest"
}
```
