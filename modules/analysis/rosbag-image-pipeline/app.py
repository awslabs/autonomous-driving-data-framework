import os

from aws_cdk import App, CfnOutput, Environment
from stack import AwsBatchPipeline

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


dag_id = os.getenv(_param("DAG_ID"))  # required
vpc_id = os.getenv(_param("VPC_ID"))  # required
mwaa_exec_role = os.getenv(_param("MWAA_EXEC_ROLE"))
full_access_policy = os.getenv(_param("FULL_ACCESS_POLICY_ARN"))
source_bucket_name = os.getenv(_param("SOURCE_BUCKET"))
target_bucket_name = os.getenv(_param("INTERMEDIATE_BUCKET"))

on_demand_job_queue = os.getenv(_param("ON_DEMAND_JOB_QUEUE_ARN"))
spot_job_queue = os.getenv(_param("SPOT_JOB_QUEUE_ARN"))
fargate_job_queue = os.getenv(_param("FARGATE_JOB_QUEUE_ARN"))
parquet_batch_job_def_arn = os.getenv(_param("PARQUET_BATCH_JOB_DEF_ARN"))
png_batch_job_def_arn = os.getenv(_param("PNG_BATCH_JOB_DEF_ARN"))
object_detection_image_uri = os.getenv(_param("OBJECT_DETECTION_IMAGE_URI"))
object_detection_role = os.getenv(_param("OBJECT_DETECTION_IAM_ROLE"))
object_detection_job_concurrency = int(os.getenv(_param("OBJECT_DETECTION_JOB_CONCURRENCY"), 10))
object_detection_instance_type = os.getenv(_param("OBJECT_DETECTION_INSTANCE_TYPE"), "ml.m5.xlarge")

lane_detection_image_uri = os.getenv(_param("LANE_DETECTION_IMAGE_URI"))
lane_detection_role = os.getenv(_param("LANE_DETECTION_IAM_ROLE"))
lane_detection_job_concurrency = int(os.getenv(_param("LANE_DETECTION_JOB_CONCURRENCY"), 5))
lane_detection_instance_type = os.getenv(_param("LANE_DETECTION_INSTANCE_TYPE"), "ml.p3.2xlarge")

file_suffix = os.getenv(_param("FILE_SUFFIX"), ".bag")
desired_encoding = os.getenv(_param("DESIRED_ENCODING"), "bgr8")
yolo_model = os.getenv(_param("YOLO_MODEL"), "yolov5s")
image_topics = os.getenv(_param("IMAGE_TOPICS"))
sensor_topics = os.getenv(_param("SENSOR_TOPICS"))

virtual_emr_cluster_id = os.getenv(_param("VIRTUAL_EMR_CLUSTER_ID"))
emr_job_role_arn = os.getenv(_param("EMR_JOB_ROLE_ARN"))

if not png_batch_job_def_arn:
    raise Exception("missing input parameter png-batch-job-def-arn")

if not parquet_batch_job_def_arn:
    raise Exception("missing input parameter parquet-batch-job-def-arn")

if not object_detection_role:
    raise Exception("missing input parameter object-detection-iam-role")

if not object_detection_image_uri:
    raise Exception("missing input parameter object-detection-image-uri")

if not lane_detection_role:
    raise Exception("missing input parameter lane-detection-iam-role")

if not lane_detection_image_uri:
    raise Exception("missing input parameter lane-detection-image-uri")

if not vpc_id:
    raise Exception("missing input parameter vpc-id")

if not mwaa_exec_role:
    raise ValueError("MWAA Execution Role is missing.")

if not full_access_policy:
    raise ValueError("S3 Full Access Policy ARN is missing.")

if not on_demand_job_queue and not spot_job_queue and not fargate_job_queue:
    raise ValueError("Requires at least one job queue.")

app = App()

stack = AwsBatchPipeline(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    vpc_id=vpc_id,
    mwaa_exec_role=mwaa_exec_role,
    bucket_access_policy=full_access_policy,
    object_detection_role=object_detection_role,
    lane_detection_role=lane_detection_role,
    job_queues=[x for x in [fargate_job_queue, spot_job_queue, on_demand_job_queue] if x is not None],
    job_definitions=[x for x in [png_batch_job_def_arn, parquet_batch_job_def_arn] if x is not None],
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)
import json

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "DagId": dag_id,
            "DagRoleArn": stack.dag_role.role_arn,
            "DynamoDbTableName": stack.tracking_table_name,
            "SourceBucketName": source_bucket_name,
            "TargetBucketName": target_bucket_name,
            "OnDemandJobQueueArn": on_demand_job_queue,
            "SpotJobQueueArn": spot_job_queue,
            "FargateJobQueueArn": fargate_job_queue,
            "ParquetBatchJobDefArn": parquet_batch_job_def_arn,
            "PngBatchJobDefArn": png_batch_job_def_arn,
            "ObjectDetectionImageUri": object_detection_image_uri,
            "ObjectDetectionRole": object_detection_role,
            "ObjectDetectionJobConcurrency": object_detection_job_concurrency,
            "ObjectDetectionInstanceType": object_detection_instance_type,
            "LaneDetectionImageUri": lane_detection_image_uri,
            "LaneDetectionRole": lane_detection_role,
            "LaneDetectionJobConcurrency": lane_detection_job_concurrency,
            "LaneDetectionInstanceType": lane_detection_instance_type,
            "FileSuffix": file_suffix,
            "DesiredEncoding": desired_encoding,
            "YoloModel": yolo_model,
            "ImageTopics": json.loads(image_topics),
            "SensorTopics": json.loads(sensor_topics),
            "EmrVirtualClusterId": virtual_emr_cluster_id,
            "EmrJobRoleArn": emr_job_role_arn,
        }
    ),
)

app.synth(force=True)
