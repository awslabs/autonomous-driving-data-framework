# AWS Batch Job and Container for Ros to Png Extraction 

## Description

This module contains a Docker container for extracting ros image topics to png files, and an accompanying
AWS Batch Job Definition to run this job at scale.

This module deploys:

- ECR Repository and ECR Image for ros-to-png extraction container
- IAM Role for Batch Job
- AWS Batch Job Definition

## Testing module

Deploy the ros-image-demo manifest
 
Trigger ros_image_pipeline dag in Airflow with a config like:"
{
    "drives_to_process": {
        "{drive_id_1}": {"bucket": "{bucket}", "prefix": "{prefix}/"},
        "{drive_id_n}": {"bucket": "{bucket_n}", "prefix": "{prefix_n}/"}
    }
}

where files exist in:
    s3://{bucket}/{prefix}/*.bag
    s3://{bucket_n}/{prefix_n}/*.bag
    
## Inputs/Outputs

### Input Parameters

#### Required

- `full-access-policy-arn`: Access policy from Datalake Bucket Core Module
- `ecr-repository-arn`: ARN of the ECR Repository
- `platform`: FARGATE or EC2 - what capacity provider should the job run on
- `retries`: how may times should a single failed container job retry?
- `timeout-seconds`: after how many seconds should a single container job timeout
- `vcpus`: how many vcpus does a container need
- `memory-mib`: how much ram does a container need

#### Optional
- `solution-id`: a unique identifier for this deployment (must be used with `solution-description`)
- `solution-name`: a unique name for this deployment (must be used with `solution-id`)
- `solution-version`: a unique version for this deployment

The parameters `(solution-*)` will resolve a custom text that is used as a description of the stack if populated.
### Sample declaration of AWS Batch Compute Configuration

```yaml
name: ros-to-png
path: modules/sensor-extraction/ros-to-png/
parameters:
  - name: platform
    value: FARGATE
  - name: retries
    value: 1
  - name: timeout-seconds
    value: 1800
  - name: vcpus
    value: 2
  - name: memory-mib
    value: 8192
  - name: full-access-policy-arn
    valueFrom:
      moduleMetadata:
        group: optionals
        name: datalake-buckets
        key: FullAccessPolicyArn
  - name: ecr-repository-arn
    valueFrom:
      moduleMetadata:
        group: docker-repositories
        name: lane-detection
        key: EcrRepositoryArn
```

### Module Metadata Outputs

- `JobDefinitionArn`: ARN of the AWS Batch Job Definition to be executed via Airflow

            
#### Output Example

```json
{
  "JobDefinitionArn":"arn:aws:batch:..."
}
```
