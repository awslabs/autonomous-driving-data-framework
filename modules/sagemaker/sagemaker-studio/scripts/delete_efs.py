# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import sys
import time
from typing import List

import boto3

client_efs = boto3.client("efs")
client_ec2 = boto3.client("ec2")


def delete_mount_target(target: str) -> None:
    client_efs.delete_mount_target(MountTargetId=target)


def delete_file_system(efs_id: str) -> None:
    client_efs.delete_file_system(FileSystemId=efs_id)


def delete_security_groups(sg_ids: List[str]) -> None:
    resp = client_ec2.describe_security_groups(GroupIds=sg_ids)

    for sg in resp["SecurityGroups"]:
        if sg["IpPermissionsEgress"]:
            client_ec2.revoke_security_group_egress(GroupId=sg["GroupId"], IpPermissions=sg["IpPermissionsEgress"])
        if sg["IpPermissions"]:
            client_ec2.revoke_security_group_ingress(GroupId=sg["GroupId"], IpPermissions=sg["IpPermissions"])

    for sg in resp["SecurityGroups"]:
        client_ec2.delete_security_group(GroupId=sg["GroupId"])


def get_mount_point_security_groups(target: str) -> List[str]:
    resp = client_efs.describe_mount_target_security_groups(MountTargetId=target)
    return resp["SecurityGroups"]


def get_security_groups(vpc_id: str, domain_id: str) -> List[str]:
    resp = client_ec2.describe_security_groups(
        Filters=[
            {
                "Name": "vpc-id",
                "Values": [
                    vpc_id,
                ],
            },
            {
                "Name": "group-name",
                "Values": [
                    f"security-group-for-inbound-nfs-{domain_id}",
                    f"security-group-for-outbound-nfs-{domain_id}",
                ],
            },
        ]
    )
    sgs = [sg["GroupId"] for sg in resp["SecurityGroups"]]
    return sgs


def process(efs_id: str, domain_id: str) -> None:
    resp = client_efs.describe_mount_targets(FileSystemId=efs_id)
    vpc_id = None
    for target in resp["MountTargets"]:
        mount_target_id = target["MountTargetId"]
        vpc_id = target["VpcId"]
        print(f"Deleting mount target {mount_target_id}")
        delete_mount_target(mount_target_id)

    print("Sleeping to allow mount targts to delete")
    time.sleep(35)
    print(f"Deleting FileSystem {efs_id}")
    delete_file_system(efs_id=efs_id)
    sgs = get_security_groups(vpc_id=vpc_id, domain_id=domain_id)
    delete_security_groups(sgs)


if __name__ == "__main__":
    efs_id = sys.argv[1]
    domain_id = sys.argv[2]
    process(efs_id, domain_id)
