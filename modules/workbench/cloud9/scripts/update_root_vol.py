import json
import logging
import os

import boto3
import botocore

LOGGING_FORMAT = "[%(asctime)s][%(filename)-13s:%(lineno)3d] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOGGING_FORMAT)
_logger: logging.Logger = logging.getLogger(__name__)

ec2_client = boto3.client("ec2")

ADDF_METADATA = json.loads(os.getenv("ADDF_MODULE_METADATA"))

cloud9_arn = ADDF_METADATA.get("Cloud9EnvArn")
cloud9_env_id = cloud9_arn.split(":")[-1]
volume_size = int(ADDF_METADATA.get("InstanceStorageSize"))

res = ec2_client.describe_instances(Filters=[{"Name": "tag:aws:cloud9:environment", "Values": [cloud9_env_id]}])

full_cloud9_instance_name = [tag["Value"] for tag in res["Reservations"][0]["Instances"][0]["Tags"] if tag["Key"] == "Name"][0]
instance_id = res["Reservations"][0]["Instances"][0]["InstanceId"]
volume_id = res["Reservations"][0]["Instances"][0]["BlockDeviceMappings"][0]["Ebs"]["VolumeId"]

try:
    ec2_client.create_tags(
        Resources=[instance_id, volume_id],
        Tags=[
            {
                "Key": "ADDF_DEPLOYMENT_NAME",
                "Value": os.getenv("ADDF_DEPLOYMENT_NAME")
            },
            {
                "Key": "ADDF_MODULE_NAME",
                "Value": os.getenv("ADDF_MODULE_NAME")
            },
            {
                "Key": "Name",
                "Value": full_cloud9_instance_name
            },
        ]
    )
except Exception as err:
    raise err

try:
    ec2_client.modify_volume(
        VolumeId=volume_id,
        Size=volume_size,
    )
except botocore.exceptions.ClientError as err:
    if err.response["Error"]["Code"] == "VolumeModificationRateExceeded":
        _logger.info(err)
    else:
        raise Exception(err)
