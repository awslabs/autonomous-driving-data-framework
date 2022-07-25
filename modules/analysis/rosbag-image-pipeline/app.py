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

raw_input_prefix = os.getenv(_param("RAW_INPUT_PREFIX"))
png_output_prefix = os.getenv(_param("PNG_OUTPUT_PREFIX"))
mp4_output_prefix = os.getenv(_param("MP4_OUTPUT_PREFIX"))

if not vpc_id:
    raise Exception("missing input parameter vpc-id")

if not mwaa_exec_role:
    raise ValueError("MWAA Execution Role is missing.")

if not full_access_policy:
    raise ValueError("S3 Full Access Policy ARN is missing.")

if not on_demand_job_queue and not spot_job_queue and not fargate_job_queue:
    raise ValueError("Requires at least one job queue.")

if not raw_input_prefix or not png_output_prefix or not mp4_output_prefix:
    raise ValueError("Requires output prefix for raw_input_prefix and png and mp4 output prefixes")


app = App()

config = {
    "deployment_name": deployment_name,
    "module_name": module_name,
    "vpc_id": vpc_id,
    "mwaa_exec_role": mwaa_exec_role,
    "full_access_policy": full_access_policy,
}

stack = AwsBatchPipeline(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    config=config,
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
            "EcrRepoName": stack.repository_name,
            "DynamoDbTableName": stack.tracking_table_name,
            "SourceBucketName": source_bucket_name,
            "TargetBucketName": target_bucket_name,
            "OnDemandJobQueueArn": on_demand_job_queue,
            "SpotJobQueueArn": spot_job_queue,
            "FargateJobQueueArn": fargate_job_queue,
            "RawInputPrefix": raw_input_prefix,
            "PngOutputPrefix": png_output_prefix,
            "Mp4OutputPrefix": mp4_output_prefix,
        }
    ),
)

app.synth(force=True)
