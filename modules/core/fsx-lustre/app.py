import json
import logging
import os

from aws_cdk import App, CfnOutput, Environment
from stack import FsxFileSystem

LOGGING_FORMAT = "[%(asctime)s][%(filename)-13s:%(lineno)3d] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOGGING_FORMAT)
_logger: logging.Logger = logging.getLogger(__name__)

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


vpc_id = os.getenv(_param("VPC_ID"))  # required
private_subnet_ids = json.loads(os.getenv(_param("PRIVATE_SUBNET_IDS")))  # type: ignore # required
fs_deployment_type = os.getenv(_param("FS_DEPLOYMENT_TYPE"), "PERSISTENT_2")  # required
import_path = os.getenv(_param("IMPORT_PATH"), None)
export_path = os.getenv(_param("EXPORT_PATH"), None)
data_bucket_name = os.getenv(_param("DATA_BUCKET_NAME"), None)
storage_throughput = os.getenv(_param("STORAGE_THROUGHPUT"), None)
storage_throughput = int(storage_throughput) if storage_throughput else None  # type: ignore


if not vpc_id:
    raise Exception("missing input parameter vpc-id")

if not private_subnet_ids:
    raise Exception("missing input parameter private-subnet-ids")

if fs_deployment_type == "PERSISTENT_2" and data_bucket_name is not None and import_path is not None:
    raise Exception("File system deployment type `PERSISTENT_2` does not support an S3 import path")

if fs_deployment_type == "PERSISTENT_2" and data_bucket_name is not None and export_path is not None:
    raise Exception("File system deployment type `PERSISTENT_2` does not support an S3 export path")

if "SCRATCH" in fs_deployment_type and storage_throughput is not None:
    _logger.warning(
        f"The storage throughput can not be specified for fs_deployment_type={fs_deployment_type}. Setting to None"
    )
    storage_throughput = None

if "PERSISTENT" in fs_deployment_type and storage_throughput is None:
    raise Exception(f"The storage throughput must be specified for Lustre fs_deployment_type={fs_deployment_type}")

app = App()

stack = FsxFileSystem(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    data_bucket_name=data_bucket_name,
    fs_deployment_type=fs_deployment_type,
    module_name=module_name,
    private_subnet_ids=private_subnet_ids,
    vpc_id=vpc_id,
    import_path=import_path,
    export_path=export_path,
    storage_throughput=storage_throughput,  # type: ignore
    env=Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region=os.environ["CDK_DEFAULT_REGION"]),
)

fsx_lustre_fs_deployment_type = stack.fsx_filesystem.lustre_configuration.deployment_type  # type: ignore

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "FSxLustreAttrDnsName": stack.fsx_filesystem.attr_dns_name,
            "FSxLustreFileSystemId": stack.fsx_filesystem.ref,
            "FSxLustreSecurityGroup": stack.fsx_security_group.security_group_id,
            "FSxLustreMountName": stack.fsx_filesystem.attr_lustre_mount_name,
            "FSxLustreFileSystemDeploymentType": fsx_lustre_fs_deployment_type,
        }
    ),
)

app.synth(force=True)
