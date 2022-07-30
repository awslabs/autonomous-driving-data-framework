# Ros Image Extraction Pipeline

## Description

This module contains an end-to-end pipeline for extracting images from Rosbag recording files using AWS Batch.
The module labels these extracted images with open-source object detection and lane detection models
using Sagemaker Processing jobs. The entire pipeline is orchestrated with a single Airflow dag.

The pipeline expects a config of a list of drives to process from S3.

This module deploys:

- IAM Role for Batch Job and Airflow Dag
- a DynamoDB table used for passing data to AWS Batch containers and Sagemaker Processing jobs.

The deployspec also includes commands to:
- build and publish images/ros-to-png to ECR for image extraction
- build and publish images/yolo to ECR for object detection
- upload image_dags/ to S3 for Managed Airflow
- append deployment variables to image_dags/dag_config.py for the DAG to use


## Testing module

Trigger ros_image_pipeline dag in Airflow with this config"
{
    "drives_to_process": {
        "drive1": {"bucket": "addf-sample-rosbag-data", "prefix": "drive1/"},
        "drive2": {"bucket": "addf-sample-rosbag-data", "prefix": "drive2/"},
        "drive3": {"bucket": "addf-sample-rosbag-data", "prefix": "drive3/"},
        "drive4": {"bucket": "addf-sample-rosbag-data", "prefix": "drive4/"},
        "smalldrive": {"bucket": "addf-sample-rosbag-data", "prefix": "small-demo/"}
    }
}

where files exist in:
    s3://addf-ros-image-demo-raw-bucket-d2be7d29/rosbag-scene-detection/drive1/*.bag
    s3://addf-ros-image-demo-raw-bucket-d2be7d29/rosbag-scene-detection/drive2/*.bag
    
## Inputs/Outputs

### Input Parameters

#### Required


- `dag-bucket-name`: name of the Bucket configured in the shared MWAA Environment to store DAG artifacts
- `dag-path`: name of the path in the Bucket configured in the shared MWAA Environment to store DAG artifacts
- `mwaa-exec-role`: ARN of the MWAA Execution Role
- `vpc-id`: The VPC-ID that the cluster will be created in
- `private-subnet-ids`: The Private Subnets that the AWS Batch Compute resources will be deployed to
- `source-bucket`: Bucket containing the raw recording data
- `intermediate-bucket`: Output bucket for saving images
- `full-access-policy-arn`: Access policy from Datalake Bucket Core Module
- `on-demand-job-queue-arn`: Job Queue ARN from Batch Compute Core Module
- `spot-job-queue-arn`: Job Queue ARN from Batch Compute Core Module
- `fargate-job-queue-arn`: Job Queue ARN from Batch Compute Core Module
    
### Sample declaration of AWS Batch Compute Configuration

```yaml
name: image-pipeline
path: modules/analysis/rosbag-image-pipeline
parameters:
  - name: vpc-id
    valueFrom:
      moduleMetadata:
        group: optionals
        name: networking
        key: VpcId
  - name: private-subnet-ids
    valueFrom:
      moduleMetadata:
        group: optionals
        name: networking
        key: PrivateSubnetIds
  - name: source-bucket
    valueFrom:
      moduleMetadata:
        group: optionals
        name: datalake-buckets
        key: RawBucketName
  - name: intermediate-bucket
    valueFrom:
      moduleMetadata:
        group: optionals
        name: datalake-buckets
        key: IntermediateBucketName
  - name: dag-bucket-name
    valueFrom:
      moduleMetadata:
        group: optionals
        name: datalake-buckets
        key: ArtifactsBucketName
  - name: dag-path
    valueFrom:
      moduleMetadata:
        group: core
        name: mwaa
        key: DagPath
  - name: full-access-policy-arn
    valueFrom:
      moduleMetadata:
        group: optionals
        name: datalake-buckets
        key: FullAccessPolicyArn
  - name: on-demand-job-queue-arn
    valueFrom:
      moduleMetadata:
        group: core
        name: batch-compute
        key: OnDemandJobQueueArn
  - name: spot-job-queue-arn
    valueFrom:
      moduleMetadata:
        group: core
        name: batch-compute
        key: SpotJobQueueArn
  - name: fargate-job-queue-arn
    valueFrom:
      moduleMetadata:
        group: core
        name: batch-compute
        key: FargateJobQueueArn
  - name: mwaa-exec-role
    valueFrom:
      moduleMetadata:
        group: core
        name: mwaa
        key: MwaaExecRoleArn

```

#### Optional

### Module Metadata Outputs

- `DagRoleArn`: ARN of the DAG Execution Role created by the Stack
- `OnDemandJobQueueArn`: ARN of the ON_DEMAND AWS Batch Queue
- `SpotJobQueueArn`: ARN of the SPOT AWS Batch Queue
- `FargateJobQueueArn`: ARN of the FARGATE AWS Batch Queue
- `EcrRepoName`: ECR Repo of the Container
- `DynamoDbTableName`: Table for orchestrating AWS Batch job
- `SourceBucketName`: Bucket containing raw data
- `TargetBucketName`: Bucket to save images and video to

            
#### Output Example

```json
{
  "DagRoleArn":"arn:aws:iam::...",
  "EcrRepoName":"addf-ros-image-demo-analysis-image-pipeline",
  "DynamoDbTableName":"addf-ros-image-demo-analysis-image-pipeline-drive-tracking",
  "SourceBucketName":"addf-ros-image-demo-raw-bucket-xyz",
  "TargetBucketName":"addf-ros-image-demo-intermediate-bucket-xyz",
  "OnDemandJobQueueArn":"arn:aws:batch:...",
  "SpotJobQueueArn":"arn:aws:batch:...",
  "FargateJobQueueArn":"arn:aws:batch:..."
}
```


from sagemaker.pytorch.processing import PyTorchProcessor
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker import get_execution_role

role = get_execution_role()


#DO NOT CHANGE THESE
LOCAL_INPUT = '/opt/ml/processing/input/image'
LOCAL_OUTPUT='/opt/ml/processing/output/image'


### CHANGE THESE!!!
BUCKET='<YOUR_BUCKET>'
S3_INPUT_PATH ='<PATH>'
S3_OUTPUT_PATH='<PATH>'
IMAGE_URI='ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/IMAGE:VERSION'
SRC_TAR_BUCKET='<YOUR_BUCKET>'
SRC_TAR_KEY='<PATH TO SOURCEDIR.TAR.GZ'  ## DOn't put the sourcedir.tar.gz name in the path


pytorch_processor = PyTorchProcessor(
    framework_version='1.8',
    role=role,
    instance_type='ml.p3.2xlarge', #ml.m4.xlarge (NO) ml.g4dn.xlarge (NO) ml.p3.2xlarge (YES) ml.p2.xlarge (YES)
    instance_count=1,
    base_job_name='Lanedet-testing',
    image_uri=IMAGE_URI,
)

#Run the processing job
pytorch_processor.run(
    code='tools/detect.py', #within source.tar.gz file
    source_dir=f's3://{SRC_TAR_BUCKET}/{SRC_TAR_KEY}', #this is sourcedir.tar.gz that needs staging
    arguments=[
        "configs/laneatt/resnet34_tusimple.py", #within source.tar.gz file
        "--img",LOCAL_INPUT,
        "--savedir",LOCAL_OUTPUT,
        "--load_from","models/laneatt_r34_tusimple.pth", #within source.tar.gz file

    ],
    inputs=[
        ProcessingInput(
            input_name='images',
            source=f's3://{BUCKET}/{S3_INPUT_PATH}',
            destination=LOCAL_INPUT
        )
    ],
    outputs=[
        ProcessingOutput(
            output_name='out', 
            source=LOCAL_OUTPUT,
            destination=f's3://{BUCKET}/{S3_OUTPUT_PATH}')
        
    ]
)