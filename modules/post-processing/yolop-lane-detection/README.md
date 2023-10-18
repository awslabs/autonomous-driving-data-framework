# Lane Detection Docker image for ECR 

## Description

This module contains a Docker container for detecting lanes on images using 
YOLOP (https://github.com/hustvl/YOLOP).  It is designed to incorporate the weights, the model code, and the transformation/processing code into one image with the entry point being `tools/detect_lanes.py` when processing. 

NOTE: this image can run on CPU and GPU compute resources

### Full list of parameters for processing code
The `tools/detect_lanes.py` entry point has several parameters that can be overridden.  Please see `tools/detect_lanes.py` for a reference as to the parameters you can override as necessary.  


### Sample Sagemaker Processing Code

A sample piece of code that leverages this image as a Sagemaker Processing job is located at `/src/sample_sm_processor.py`.  The `/src/sample_sm_processor.py` is a working example that does not modify the processing code, only provides references to the images on S3 and where the output should be placed on S3.


    
## Inputs/Outputs

### Input Parameters

#### Required

- `full-access-policy-arn`: Access policy from Datalake Bucket Core Module

#### Optional
- `removal-policy`: Elect to retain ECR repositories when deleting stacks
- `solution-id`: a unique identifier for this deployment (must be used with `solution-description`)
- `solution-name`: a unique name for this deployment (must be used with `solution-id`)
- `solution-version`: a unique version for this deployment

The parameters `(solution-*)` will resolve a custom text that is used as a description of the stack if populated.
    
### Sample declaration 

```yaml
name: lane-detection
path: modules/post-processing/yolop-lane-detection/
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

                        
#### Output Example

```json
{
  "EcrRepoName": "addf-ros-image-demo-docker-images-yolop-lane-detection", 
  "ExecutionRole": "arn:aws:iam::123456789012:role/addf-ros-image-demo-docke-addfrosimagedemodockerim-V62UW5SWGPIF", 
  "ImageUri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/addf-ros-image-demo-docker-images-yolop-lane-detection:smprocessor"}
```
