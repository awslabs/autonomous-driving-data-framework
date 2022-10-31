import json
import os

from aws_cdk import App, CfnOutput, Environment

from stack import AwsBatch

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


vpc_id = os.getenv(_param("VPC_ID"))  # required
private_subnet_ids = json.loads(os.getenv(_param("PRIVATE_SUBNET_IDS"), ""))  # required
batch_compute = json.loads(os.getenv(_param("BATCH_COMPUTE"), ""))  # required
ebs_iops = int(os.getenv(_param("EBS_IOPS"), 1000))
ebs_size_gbs = int(os.getenv(_param("EBS_SIZE_GBS"), 100))
ebs_type = os.getenv(_param("EBS_TYPE"), "io1")

if ebs_iops / ebs_size_gbs >= 50:
    raise Exception("iops cannot be more than 50x ebs volume size")

if not vpc_id:
    raise Exception("Missing input parameter vpc-id")

if not private_subnet_ids:
    raise Exception("Missing input parameter private-subnet-ids")

if not batch_compute:
    raise ValueError("Batch Compute Configuration is missing.")


app = App()

stack = AwsBatch(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    vpc_id=vpc_id,
    private_subnet_ids=private_subnet_ids,
    batch_compute=batch_compute,
    ebs_iops=ebs_iops,
    ebs_size_gbs=ebs_size_gbs,
    ebs_type=ebs_type,
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
            "BatchPolicyString": stack.batch_policy_document,
            "BatchSecurityGroupId": stack.batch_sg,
            "OnDemandJobQueueArn": stack.on_demand_jobqueue.job_queue_arn
            if stack.on_demand_jobqueue.job_queue_arn
            else "QUEUE NOT CREATED",
            "SpotJobQueueArn": stack.spot_jobqueue.job_queue_name
            if stack.spot_jobqueue.job_queue_name
            else "QUEUE NOT CREATED",
            "FargateJobQueueArn": stack.fargate_jobqueue.job_queue_name
            if stack.fargate_jobqueue.job_queue_name
            else "QUEUE NOT CREATED",
        }
    ),
)

app.synth(force=True)
