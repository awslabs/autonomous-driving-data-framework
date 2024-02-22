
# Ros Image Extraction Pipeline


## Description

A Step Functions pipeline which extracts images from Rosbag recording files using AWS Batch, and labels them using open-source object detection and lane detection models in SageMaker processing jobs. The pipeline expects a config of a list of drives to process from S3.

This module deploys:

- A Step Function workflow
- a DynamoDB table used for passing data to AWS Batch containers and Sagemaker Processing jobs


## Inputs/Outputs

### Input Paramenters

#### Required

- `parquet-batch-job-def-arn`: ARN of the Batch Job Definition for extracting sensor data to Parquet files
- `png-batch-job-def-arn`: ARN of the Batch Job Definition for extracting image data to PNG files
- `object-detection-image-uri`: ECR URI of the image for running object detection models
- `object-detection-job-concurrency`: max number of parallel SageMaker processing jobs to trigger
- `object-detection-iam-role`: execution role of the object detection container
- `object-detection-instance-type`: instance type to use for the SageMaker processing job for object detection
- `lane-detection-image-uri`: ECR URI of the image for running lane detection models
- `lane-detection-job-concurrency`: max number of parallel SageMaker processing jobs to trigger
- `lane-detection-iam-role`: execution role of the lane detection container
- `lane-detection-instance-type`: instance type to use for the SageMaker processing job for lane detection
- `emr-job-exec-role`: ARN of the role for executing EMR serverless jobs
- `emr-app-id`: ID of the EMR serverless app
- `artifacts-bucket-name`: name of the S3 bucket to store DAG artifacts
- `source-bucket-name`: name of the S3 bucket which contains the Rosbag files
- `intermediate-bucket-name`: name of the output S3 bucket for saving images
- `logs-bucket-name`: name of the S3 bucket for storing logs
- `vpc-id`: The VPC-ID that the SageMaker processing jobs will run in
- `on-demand-job-queue-arn`: Job Queue ARN from Batch Compute Core Module
- `fargate-job-queue-arn`: Job Queue ARN from Batch Compute Core Module
- `rosbag-scene-metadata-table`: Name of the DynamoDB table to store Rosbag scene metadata
- `image-topics`: List of image topics
- `sensor-topics`: List of sensor topics

#### Optional

- `solution-id`: a unique identifier for this deployment (must be used with `solution-description`)
- `solution-name`: a unique name for this deployment (must be used with `solution-id`)
- `solution-version`: a unique version for this deployment

The parameters `(solution-*)` will resolve a custom text that is used as a description of the stack if populated.

### Sample declaration

```yaml
name: image-pipeline
path: modules/analysis/rosbag-image-pipeline-sfn
parameters:
  - name: image-topics
    value:
      - /flir_adk/rgb_front_left/image_raw
      - /flir_adk/rgb_front_right/image_raw
  - name: sensor-topics
    value:
      - /vehicle/gps/fix
      - /vehicle/gps/time
      - /vehicle/gps/vel
      - /imu_raw
  - name: desired-encoding
    value: bgr8
  - name: lane-detection-job-concurrency
    value: 20
  - name: lane-detection-instance-type
    value: ml.m5.2xlarge
  - name: lane-detection-image-uri
    valueFrom:
      moduleMetadata:
        group: docker-images
        name: lane-detection
        key: ImageUri
  - name: lane-detection-iam-role
    valueFrom:
      moduleMetadata:
        group: docker-images
        name: lane-detection
        key: ExecutionRole
  - name: object-detection-job-concurrency
    value: 30
  - name: object-detection-instance-type
    value: ml.m5.xlarge
  - name: object-detection-image-uri
    valueFrom:
      moduleMetadata:
        group: docker-images
        name: object-detection
        key: ImageUri
  - name: object-detection-iam-role
    valueFrom:
      moduleMetadata:
        group: docker-images
        name: object-detection
        key: ExecutionRole
  - name: parquet-batch-job-def-arn
    valueFrom:
      moduleMetadata:
        group: docker-images
        name: ros-to-parquet
        key: JobDefinitionArn
  - name: png-batch-job-def-arn
    valueFrom:
      moduleMetadata:
        group: docker-images
        name: ros-to-png
        key: JobDefinitionArn
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
  - name: rosbag-scene-metadata-table
    valueFrom:
      moduleMetadata:
        group: core
        name: metadata-storage
        key: RosbagSceneMetadataTable
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
  - name: artifacts-bucket-name
    valueFrom:
      moduleMetadata:
        group: optionals
        name: datalake-buckets
        key: ArtifactsBucketName
  - name: logs-bucket-name
    valueFrom:
      moduleMetadata:
        group: optionals
        name: datalake-buckets
        key: LogsBucketName
  - name: on-demand-job-queue-arn
    valueFrom:
      moduleMetadata:
        group: core
        name: batch-compute
        key: OnDemandJobQueueArn
  - name: fargate-job-queue-arn
    valueFrom:
      moduleMetadata:
        group: core
        name: batch-compute
        key: FargateJobQueueArn
  - name: emr-job-exec-role
    valueFrom:
      moduleMetadata:
        group: core
        name: emr-serverless
        key: EmrJobExecutionRoleArn
  - name: emr-app-id
    valueFrom:
      moduleMetadata:
        group: core
        name: emr-serverless
        key: EmrApplicationId
  - name: solution-id
    value: 'SO0279-M'
  - name: solution-name
    value: 'Scene Intelligence with Rosbag on AWS'
  - name: solution-version
    value: v1.0.0
```

### Module Metadata Outputs

- `StateMachineArn`: ARN of the state machine

#### Output Example

```json
{
    "StateMachineArn": "arn:aws:states:*",
}



