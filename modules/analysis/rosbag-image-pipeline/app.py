import os

from aws_cdk import App, CfnOutput, Environment
from stack import AwsBatchPipeline

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


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
object_detection_job_concurrency = int(os.getenv(_param("OBJECT_DETECTION_JOB_CONCURRENCY"), 30))
object_detection_instance_type = os.getenv(_param("OBJECT_DETECTION_INSTANCE_TYPE"), "ml.m5.xlarge")

if not png_batch_job_def_arn:
    raise Exception("missing input parameter png-batch-job-def-arn")

if not parquet_batch_job_def_arn:
    raise Exception("missing input parameter parquet-batch-job-def-arn")

if not object_detection_role:
    raise Exception("missing input parameter object-detection-iam-role")

if not object_detection_image_uri:
    raise Exception("missing input parameter object-detection-image-uri")

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
    job_queues=[x for x in [fargate_job_queue, spot_job_queue, on_demand_job_queue] if x is not None],
    job_definitions=[x for x in [png_batch_job_def_arn, parquet_batch_job_def_arn] if x is not None],
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
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
        }
    ),
)

app.synth(force=True)
