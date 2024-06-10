# AWS Batch Job and Container for Ros to Png Extraction 

## Description

This module contains a Docker container for labelling images with a YOLOv8 Object Detection model.
The container is designed to run at scale with a Sagemaker Processing job.

This module deploys:

- ECR Repository and ECR Image for yolo object detection container
- IAM Role for Sagemaker Processing job

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

#### Optional
- `solution-id`: a unique identifier for this deployment (must be used with `solution-description`)
- `solution-name`: a unique name for this deployment (must be used with `solution-id`)
- `solution-version`: a unique version for this deployment

The parameters `(solution-*)` will resolve a custom text that is used as a description of the stack if populated.
    
### Sample declaration of AWS Batch Compute Configuration

```yaml
name: object-detection
path: modules/post-processing/yolo-object-detection/
parameters:
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

- `ImageUri`: ecr uri of the image 
- `EcrRepoName`: ecr repo name for the image
- `ExecutionRole`: ARN of the IAM Role for running the container
- `BaseImage`: Base Deep Learning image to use for the container build

                        
#### Output Example

```json
{
    "ImageUri":"arn:aws:batch:...",
    "EcrRepoName":"arn:aws:batch:...",
    "ExecutionRole":"arn:aws:batch:...",
    "BaseImage":"arn:aws:batch:..."
}
```
