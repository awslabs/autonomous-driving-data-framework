# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# type: ignore
""" Stack for DataServiceDevInstances """
import json
import os
from typing import cast

import aws_cdk.aws_secretsmanager as secretsmanager
from aws_cdk import Environment, SecretValue, Stack, Tags, aws_iam
from aws_cdk.aws_ec2 import (
    BlockDevice,
    BlockDeviceVolume,
    EbsDeviceVolumeType,
    Instance,
    InstanceType,
    MachineImage,
    OperatingSystemType,
    Peer,
    Port,
    SecurityGroup,
    SubnetSelection,
    SubnetType,
    UserData,
    Vpc,
)
from constructs import Construct, IConstruct

SSM_PARAMETER_MAP: dict = {
    "focal": "/aws/service/canonical/ubuntu/server/focal/stable/current/amd64/hvm/ebs-gp2/ami-id",
    "jammy": "/aws/service/canonical/ubuntu/server/jammy/stable/current/arm64/hvm/ebs-gp2/ami-id",
    "noble": "/aws/service/canonical/ubuntu/server/noble/stable/current/amd64/hvm/ebs-gp3/ami-id",
}
STACK_DESCRIPTION = "(SO9154) Autonomous Driving Data Framework (ADDF) - dev-instance-foxbox"


class DataServiceDevInstancesStack(Stack):
    """Dev Instance Class"""

    _user_data: str = None

    # pylint: disable=R0913,R0914
    def __init__(
        self,
        scope: Construct,
        stack_id: str,
        *,
        env: Environment,
        deployment_name: str,
        module_name: str,
        vpc_id: str,
        instance_count: int = 1,
        ami_id: str = None,
        instance_type: str = "g4dn.xlarge",
        ebs_volume_size: int = 200,
        ebs_encrypt: bool = True,
        ebs_delete_on_termination: bool = True,
        ebs_volume_type: EbsDeviceVolumeType = EbsDeviceVolumeType.GP3,
        demo_password: str = None,
        s3_bucket_dataset: str = None,
        s3_bucket_scripts: str = None,
        **kwargs,
    ) -> None:
        """Constructor"""
        super().__init__(scope, stack_id, description=STACK_DESCRIPTION, env=env, **kwargs)
        ###################
        # Initial Variables
        region = Stack.of(self).region
        prefix = stack_id

        ###################
        # Tags
        Tags.of(scope=cast(IConstruct, self)).add(key="DeploymentName", value=f"addf-{deployment_name}")

        ###################
        # AMI Selection
        ami_selected = SSM_PARAMETER_MAP.get(ami_id, SSM_PARAMETER_MAP.get("focal"))
        if ami_id is not None:
            ami = MachineImage.lookup(name=ami_id)
        else:
            ami = MachineImage.from_ssm_parameter(ami_selected, os=OperatingSystemType.LINUX)

        ###################
        # VPC
        vpc = Vpc.from_lookup(self, "VPC", vpc_id=vpc_id)

        ###################
        # Security Groups
        instance_sg = SecurityGroup(
            self,
            id="instance-sg",
            security_group_name=f"{prefix}-sg",
            allow_all_outbound=True,
            vpc=vpc,
        )
        instance_sg.add_ingress_rule(
            Peer.any_ipv4(),
            Port.tcp(8443),
            "Allow 8443 access everywhere (NiceDCV)",
        )

        ###################
        # IAM Roles
        dev_instance_role = aws_iam.Role(
            self,
            "dev-instance-role",
            assumed_by=aws_iam.CompositePrincipal(
                aws_iam.ServicePrincipal("ec2.amazonaws.com"), aws_iam.ServicePrincipal("ssm.amazonaws.com")
            ),
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedEC2InstanceDefaultPolicy"),
            ],
        )

        custom_policies = {}
        custom_policies["cloudformation"] = {
            "sid": "AllowCloudformation",
            "Effect": "Allow",
            "Action": ["cloudformation:DescribeStacks"],
            "Resource": [Stack.of(self).stack_id],
        }

        custom_policies["dcv_license"] = {
            "sid": "AllowDCVLicense",
            "Effect": "Allow",
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::dcv-license.{region}/*"],
        }

        custom_policies["s3"] = {
            "sid": "AllowADDFS3Buckets",
            "Effect": "Allow",
            "Action": ["s3:Get*", "s3:List*", "s3:PutObject*", "s3:DeleteObject*"],
            "Resource": ["arn:aws:s3:::addf*", "arn:aws:s3:::addf*/*"],
        }

        custom_policies["lambda"] = {
            "sid": "AllowADDFLambdas",
            "Effect": "Allow",
            "Action": ["lambda:Invoke*"],
            "Resource": [f"arn:aws:lambda:{self.region}:{self.account}:function:addf-*"],
        }

        if s3_bucket_dataset:
            custom_policies["s3_dataset"] = {
                "sid": "AllowDatasetsS3Buckets",
                "Effect": "Allow",
                "Action": ["s3:Get*", "s3:List*"],
                "Resource": [f"arn:aws:s3:::{s3_bucket_dataset}", f"arn:aws:s3:::{s3_bucket_dataset}/*"],
            }

        # Add the policies to the role
        # pylint: disable=W0612
        for policy_key, policy in custom_policies.items():
            dev_instance_role.add_to_principal_policy(aws_iam.PolicyStatement.from_json(policy))

        i_output = {}

        ###################
        # Instances Iterator
        for idx in range(0, instance_count):
            instance_name = f"{module_name}-{idx}"

            ###################
            # Secret Manager (Ubuntu Password)
            if not demo_password:
                secret_password = secretsmanager.SecretStringGenerator(
                    secret_string_template=json.dumps({"username": "ubuntu"}),
                    generate_string_key="password",
                    exclude_punctuation=True,
                    include_space=False,
                    exclude_characters=r"\"',. |<>=/\\#;@[]{}~:`\$",
                    password_length=24,
                )
            else:
                secret_password = {
                    "username": SecretValue.unsafe_plain_text("ubuntu"),
                    "password": SecretValue.unsafe_plain_text(demo_password),
                }

            secret = secretsmanager.Secret(
                self,
                f"{prefix}-Secret-{idx}",
                description=f"Ubuntu password for {instance_name}",
                secret_name=f"{prefix}-{idx}-ubuntu-password",
                secret_object_value=secret_password if demo_password else None,
                generate_secret_string=secret_password if not demo_password else None,
            )
            secret.grant_read(dev_instance_role)

            ###################
            # User Data
            user_data_script = self.get_user_data()
            user_data_script = user_data_script.replace(
                'SERVICE_USER_SECRET_NAME="PLACEHOLDER_SECRET"', f'SERVICE_USER_SECRET_NAME="{secret.secret_name}"'
            )
            if s3_bucket_scripts:
                user_data_script = user_data_script.replace(
                    'S3_BUCKET_NAME="PLACEHOLDER_S3_BUCKET_NAME"', f'S3_BUCKET_NAME="{s3_bucket_scripts}"'
                )
                user_data_script = user_data_script.replace(
                    'SCRIPTS_PATH="PLACEHOLDER_SCRIPTS_PATH"',
                    f'SCRIPTS_PATH="{deployment_name}-{module_name}/scripts/"',
                )

            ###################
            # Instance resource
            instance = Instance(
                self,
                id=instance_name,
                machine_image=ami,
                instance_type=InstanceType(instance_type_identifier=instance_type),
                block_devices=[
                    BlockDevice(
                        device_name="/dev/sda1",
                        volume=BlockDeviceVolume.ebs(
                            encrypted=ebs_encrypt,
                            delete_on_termination=ebs_delete_on_termination,
                            volume_size=ebs_volume_size,
                            volume_type=ebs_volume_type,
                        ),
                    )
                ],
                vpc=vpc,
                user_data=UserData.custom(user_data_script),
                role=dev_instance_role,
                vpc_subnets=SubnetSelection(subnet_type=SubnetType.PUBLIC),
                security_group=instance_sg,
                require_imdsv2=True
            )

            self.instance = instance
            i_output[instance_name] = {
                "DevInstanceURL": f"https://{instance.instance_public_dns_name}:8443",
                "AWSSecretName": secret.secret_name,
            }
        self.output_instances = i_output

    def get_user_data(self):
        """Get User Data"""
        if not self._user_data:
            with open(os.path.join("user-data", "script.sh"), "r", encoding="utf-8") as f:
                self._user_data = f.read()
        return self._user_data
