# AWS Batch Job and Container for Ros to Png Extraction 

## Description

This module contains a Docker container for labelling images with a Yolov5 Object Detection model.
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
