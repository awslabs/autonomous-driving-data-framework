# Lane Detection Docker image for ECR 

## Description

This module contains a Docker container for detecting lanes on images using 
LaneDet (https://github.com/Turoad/lanedet), with the resnet34_tusimple backbone (configs and weights).  It is designed to incorporate the weights, the model code, and the transformation/processing code into one image with the entry point being `tools/detect_lanes.py` when processing.  That entry point as one (1) positional required arguement to indicate the local path to the configuration (`configs/laneatt/resnet34_tusimple.py` in this case).  

### Full list of parameters for processing code
The `tools/detect_lanes.py` entry point has several parameters that can be overridden.  They are listed below just for reference, but you DO NOT need to modify them as they exist in the sample `/src/sample_sm_processor.py`.
* <b>config</b> - the relative path to the config file in the image (corresponds to the backbone used)
    * defaults to `configs/laneatt/resnet34_tusimple.py`
* <b>--img</b> - the local path there the images will be staged (DO NOT CHANGE)
    *  defaults to `/opt/ml/processing/input/image`
* <b>--savedir</b> -  the local path there the images will be staged (DO NOT CHANGE)
    * defaults to `/opt/ml/processing/output/image`
* <b>--load_from</b> - the local relative path to the model weights (DO NOT CHANGE)
    * defaults to `models/laneatt_r34_tusimple.pth`
* <b>--json_path</b> - the local path where the correspond JSON will be staged (not required)
    * no default set...if None, then is skipped
* <b>--csv_path</b> - the local path where the correspond JSON will be staged (not required)
    * no default set...if None, then is skipped

### Sample Sagemaker Processing Code
A sample piece of code that leverages this image as a Sagemaker Processing job is located at `/src/sample_sm_processor.py`.  This image CAN be reconfigured to run as a PyTorchProcessing job in SM, but that requires the following changes:
- a new image that does not have the supporting processing code or weights
- a `sourcedir.tar.gz` that has the weights and processing code
- a new python code (similar to `tools/detect_lanes.py`) that leverages the PytorchProcessor classes and the artifacts above.

    
## Inputs/Outputs

### Input Parameters

#### Required

- `full-access-policy-arn`: Access policy from Datalake Bucket Core Module
    
### Sample declaration 

```yaml
name: lane-detection
path: modules/post-processing/lane-detection/
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
  "EcrRepoName": "addf-ros-image-demo-docker-images-lane-detection",
  "ExecutionRole": "arn:aws:iam::123456789012:role/addf-ros-image-demo-docke-addfrosimagedemodockerim-123456789012",
  "ImageUri": "123456789012.dkr.ecr.us-east-1.amazonaws.com/addf-ros-image-demo-docker-images-lane-detection:smprocessor"
}
```
