# Ros Image Extraction Pipeline

## Description

This module contains an end-to-end pipeline for extracting images from Rosbag recording files using AWS Batch.
The module labels these extracted images with open-source object detection and lane detection models
using Sagemaker Processing jobs. The entire pipeline is orchestrated with a single Airflow dag. 
The pipeline also extracts a given set of topics to parquet files. 
The pipeline expects a config of a list of drives to process from S3.

This module deploys:

- IAM Role for the Airflow Dag
- a DynamoDB table used for passing data to AWS Batch containers and Sagemaker Processing jobs.

The deployspec also includes commands to:
- upload image_dags/ to S3 for Managed Airflow
- append deployment variables to image_dags/dag_config.py for the DAG to use


## Testing module

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

- `parquet-batch-job-def-arn`: arn of the Batch Job Definition for extracting sensor data to parquet files
- `png-batch-job-def-arn`: arn of the Batch Job Definition for extracting image data to png files
- `object-detection-image-uri`: ecr uri of the image for running object detection models
- `object-detection-job-concurrency`: max number of parallel sagemaker processing jobs to trigger
- `object-detection-iam-role`: execution role of the object detection container
- `object-detection-instance-type`: instance type to use for the Sagemaker processing job for object detection
- `dag-bucket-name`: name of the Bucket configured in the shared MWAA Environment to store DAG artifacts
- `dag-path`: name of the path in the Bucket configured in the shared MWAA Environment to store DAG artifacts
- `mwaa-exec-role`: ARN of the MWAA Execution Role
- `vpc-id`: The VPC-ID that the cluster will be created in
- `source-bucket`: Bucket containing the raw recording data
- `intermediate-bucket`: Output bucket for saving images
- `full-access-policy-arn`: Access policy from Datalake Bucket Core Module
- `on-demand-job-queue-arn`: Job Queue ARN from Batch Compute Core Module
- `spot-job-queue-arn`: Job Queue ARN from Batch Compute Core Module
- `fargate-job-queue-arn`: Job Queue ARN from Batch Compute Core Module

#### Optional
- `solution-id`: a unique identifier for this deployment (must be used with `solution-description`)
- `solution-name`: a unique name for this deployment (must be used with `solution-id`)
- `solution-version`: a unique version for this deployment

The parameters `(solution-*)` will resolve a custom text that is used as a description of the stack if populated.
    
### Sample declaration of AWS Batch Compute Configuration

```yaml
name: image-pipeline
path: modules/analysis/rosbag-image-pipeline
parameters:
  - name: object-detection-job-concurrency
    value: 50
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
- `ParquetBatchJobDefArn`: arn of the Batch Job Definition for extracting sensor data to parquet files
- `PngBatchJobDefArn`: arn of the Batch Job Definition for extracting image data to png files
- `ObjectDetectionImageUri`: ecr uri of the image for running object detection models
- `ObjectDetectionJobConcurrency`: max number of parallel sagemaker processing jobs to trigger
- `ObjectDetectionRole`: execution role of the object detection container
- `ObjectDetectionInstanceType`: instance type to use for the Sagemaker processing job for object detection


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
  "FargateJobQueueArn":"arn:aws:batch:...",
  "ParquetBatchJobDefArn":"arn:aws:batch:...",
  "PngBatchJobDefArn":"arn:aws:batch:...",
  "ObjectDetectionImageUri":"account_id.dkr.ecr.region.amazonaws.com/addf...:latest",
  "ObjectDetectionRole":"arn:aws:iam::...",
  "ObjectDetectionJobConcurrency":50,
  "ObjectDetectionInstanceType":"ml.m5.xlarge"
}



```
