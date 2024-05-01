# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# type: ignore

import json
import os
from typing import cast

import aws_cdk.aws_secretsmanager as secretsmanager
from aws_cdk import Environment, Stack, Tags, aws_iam
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

default_ami_ssm_parameter_name: str = (
    "/aws/service/canonical/ubuntu/server/focal/stable/current/amd64/hvm/ebs-gp2/ami-id"
)


class DataServiceDevInstancesStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
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
        s3_dataset_bucket: str = None,
        s3_script_bucket: str = None,
        **kwargs,
    ) -> None:
        super().__init__(
            scope, id, description="(SO9154) Autonomous Driving Data Framework (ADDF) - dev-instance", env=env, **kwargs
        )
        Tags.of(scope=cast(IConstruct, self)).add(key="DeploymentName", value=f"addf-{deployment_name}")

        region = Stack.of(self).region
        dep_mod = f"addf-{deployment_name}-{module_name}"

        ####################################################################################################
        # VPC
        ####################################################################################################
        vpc = Vpc.from_lookup(self, "VPC", vpc_id=vpc_id)

        if ami_id is not None:
            ami = MachineImage.lookup(name=ami_id)
        else:
            ami = MachineImage.from_ssm_parameter(default_ami_ssm_parameter_name, os=OperatingSystemType.LINUX)

        instance_sg = SecurityGroup(
            self,
            id="instance-sg",
            security_group_name=f"{module_name}-dev-instance-sg",
            allow_all_outbound=True,
            vpc=vpc,
        )
        instance_sg.add_ingress_rule(
            Peer.any_ipv4(),
            Port.tcp(8443),
            "allow 8443 access everywhere",
        )

        with open(os.path.join("user-data", "script.sh"), "r") as f:
            user_data_script = f.read()

        dev_instance_role = aws_iam.Role(
            self,
            "dev-instance-role",
            assumed_by=aws_iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")],
        )

        cloudformation_policy_json = {
            "Effect": "Allow",
            "Action": ["cloudformation:DescribeStacks"],
            "Resource": [Stack.of(self).stack_id],
        }

        dcv_license_policy_json = {
            "Effect": "Allow",
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::dcv-license.{region}/*"],
        }

        s3_policy_json = {
            "Effect": "Allow",
            "Action": ["s3:Get*", "s3:List*", "s3:PutObject*", "s3:DeleteObject*"],
            "Resource": ["arn:aws:s3:::addf*", "arn:aws:s3:::addf*/*"],
        }

        lambda_policy_json = {
            "Effect": "Allow",
            "Action": ["lambda:Invoke*"],
            "Resource": [f"arn:aws:lambda:{self.region}:{self.account}:function:addf-*"],
        }

        if s3_dataset_bucket:
            public_aev_dataset_policy_json = {
                "Effect": "Allow",
                "Action": ["s3:Get*", "s3:List*"],
                "Resource": [f"arn:aws:s3:::{s3_dataset_bucket}", f"arn:aws:s3:::{s3_dataset_bucket}/*"],
            }

        # Add the policies to the role
        dev_instance_role.add_to_principal_policy(aws_iam.PolicyStatement.from_json(cloudformation_policy_json))
        dev_instance_role.add_to_principal_policy(aws_iam.PolicyStatement.from_json(dcv_license_policy_json))
        dev_instance_role.add_to_principal_policy(aws_iam.PolicyStatement.from_json(s3_policy_json))
        dev_instance_role.add_to_principal_policy(aws_iam.PolicyStatement.from_json(lambda_policy_json))
        if s3_dataset_bucket:
            dev_instance_role.add_to_principal_policy(aws_iam.PolicyStatement.from_json(public_aev_dataset_policy_json))

        i_output = {}

        for idx in range(0, instance_count):
            instance_name = f"dev-instance-{idx}"
            secret = secretsmanager.Secret(
                self,
                f"Secret-{idx}",
                description=f"Ubuntu password for {instance_name}",
                secret_name=f"{dep_mod}-{idx}-ubuntu-password",
                generate_secret_string=secretsmanager.SecretStringGenerator(
                    secret_string_template=json.dumps({"username": "ubuntu"}),
                    generate_string_key="password",
                    exclude_punctuation=True,
                    include_space=False,
                    exclude_characters="',. |<>=/\"\\\$#;@[]{}~:`",
                    password_length=24,
                )
                if not demo_password
                else None,
                secret_string_beta1=secretsmanager.SecretStringValueBeta1.from_unsafe_plaintext(
                    json.dumps({"username": "ubuntu", "password": demo_password})
                )
                if demo_password
                else None,
            )
            secret.grant_read(dev_instance_role)

            user_data_script = user_data_script.replace("$DATA_SERVICE_USER_SECRET_NAME_REF", secret.secret_name)
            if s3_script_bucket:
                user_data_script = user_data_script.replace("$S3_SCRIPT_BUCKET", s3_script_bucket)
                user_data_script = user_data_script.replace("$SCRIPT_PATH", f"{deployment_name}-{module_name}/scripts/")

            self.secret = secret

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
            )

            self.instance = instance
            i_output[instance_name] = {
                "DevInstanceURL": f"https://{instance.instance_public_dns_name}:8443",
                "AWSSecretName": secret.secret_name,
            }
        self.output_instances = i_output
