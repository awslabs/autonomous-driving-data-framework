import json
import os

from aws_cdk import App, CfnOutput, Environment
from stack import FsxFileSystem

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


vpc_id = os.getenv(_param("VPC_ID"))  # required
private_subnet_ids = json.loads(os.getenv(_param("PRIVATE_SUBNET_IDS")))  # required
raw_bucket_name = os.getenv(_param("RAW_BUCKET_NAME"))
interm_bucket_name = os.getenv(_param("INTERMEDIATE_BUCKET_NAME"))
curated_bucket_name = os.getenv(_param("CURATED_BUCKET_NAME"))


if not vpc_id:
    raise Exception("missing input parameter vpc-id")

if not private_subnet_ids:
    raise Exception("missing input parameter private-subnet-ids")

app = App()

stack = FsxFileSystem(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    vpc_id=vpc_id,
    private_subnet_ids=private_subnet_ids,
    raw_bucket_name=raw_bucket_name,
    interm_bucket_name=interm_bucket_name,
    curated_bucket_name=curated_bucket_name,
    env=Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region=os.environ["CDK_DEFAULT_REGION"]),
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "FsxLustreFileSystemId": stack.fsx_filesystem.ref,
            "FsxLustreAttrDnsName": stack.fsx_filesystem.attr_dns_name,
            "FsxLustreAttrMountName": stack.fsx_filesystem.attr_lustre_mount_name,
        }
    ),
)

app.synth(force=True)
