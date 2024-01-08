# type: ignore
from typing import Dict, List, Optional

import constructs
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_emr_launch.constructs.emr_constructs import emr_code
from aws_emr_launch.constructs.emr_constructs.cluster_configuration import InstanceMarketType
from aws_emr_launch.constructs.managed_configurations.instance_group_configuration import InstanceGroupConfiguration


class TaskInstanceGroupConfiguration(InstanceGroupConfiguration):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        *,
        configuration_name: str,
        subnet: ec2.Subnet,
        namespace: str = "default",
        release_label: Optional[str] = "emr-5.29.0",
        master_instance_type: Optional[str] = "m5.2xlarge",
        master_instance_market: Optional[InstanceMarketType] = InstanceMarketType.ON_DEMAND,
        core_instance_type: Optional[str] = "m5.xlarge",
        core_instance_market: Optional[InstanceMarketType] = InstanceMarketType.ON_DEMAND,
        core_instance_count: Optional[int] = 2,
        task_instance_type: Optional[str] = "m5.xlarge",
        task_instance_market: Optional[InstanceMarketType] = InstanceMarketType.ON_DEMAND,
        task_instance_count: Optional[int] = 2,
        applications: Optional[List[str]] = None,
        bootstrap_actions: Optional[List[emr_code.EMRBootstrapAction]] = None,
        configurations: Optional[List[dict]] = None,
        step_concurrency_level: Optional[int] = 1,
        description: Optional[str] = None,
        secret_configurations: Optional[Dict[str, secretsmanager.Secret]] = None,
        core_instance_ebs_size: Optional[int] = 0,
        core_instance_ebs_type: Optional[str] = "io1",
        core_instance_ebs_iops: Optional[int] = 0,
        task_instance_ebs_size: Optional[int] = 32,
    ):

        super().__init__(
            scope,
            id,
            subnet=subnet,
            configuration_name=configuration_name,
            namespace=namespace,
            release_label=release_label,
            applications=applications,
            bootstrap_actions=bootstrap_actions,
            configurations=configurations,
            use_glue_catalog=True,
            step_concurrency_level=step_concurrency_level,
            description=description,
            secret_configurations=secret_configurations,
            master_instance_type=master_instance_type,
            master_instance_market=master_instance_market,
            core_instance_type=core_instance_type,
            core_instance_market=core_instance_market,
            core_instance_count=core_instance_count,
        )
        master_instance = {
            "Name": "Master",
            "InstanceRole": "MASTER",
            "InstanceType": master_instance_type,
            "Market": master_instance_market.name,
            "InstanceCount": 1,
        }

        core = {
            "Name": "Core",
            "InstanceRole": "CORE",
            "InstanceType": core_instance_type,
            "Market": core_instance_market.name,
            "InstanceCount": core_instance_count,
        }

        if core_instance_ebs_size > 0:
            core["EbsConfiguration"] = {
                "EbsBlockDeviceConfigs": [
                    {
                        "VolumeSpecification": {
                            "SizeInGB": core_instance_ebs_size,
                            "VolumeType": core_instance_ebs_type,
                            "Iops": core_instance_ebs_iops,  # FIXME - only for certain volume types?
                        },
                        "VolumesPerInstance": 1,
                    }
                ],
                "EbsOptimized": True,
            }

        instances = [
            master_instance,
            core,
        ]

        config = self.config
        config["Instances"]["Ec2SubnetId"] = subnet.subnet_id
        config["Instances"]["InstanceGroups"] = instances
        overrides = {
            "MasterInstanceType": {
                "JsonPath": "Instances.InstanceGroups.0.InstanceType",
                "Default": master_instance_type,
            },
            "MasterInstanceMarket": {
                "JsonPath": "Instances.InstanceGroups.0.Market",
                "Default": master_instance_market.value,
            },
            "CoreInstanceCount": {
                "JsonPath": "Instances.InstanceGroups.1.InstanceCount",
                "Default": core_instance_count,
            },
            "CoreInstanceType": {
                "JsonPath": "Instances.InstanceGroups.1.InstanceType",
                "Default": core_instance_type,
            },
            "CoreInstanceMarket": {
                "JsonPath": "Instances.InstanceGroups.1.Market",
                "Default": core_instance_market.value,
            },
            "Subnet": {
                "JsonPath": "Instances.Ec2SubnetId",
                "Default": subnet.subnet_id,
            },
        }

        if task_instance_count > 0:
            instances.append(
                {
                    "Name": "Task",
                    "InstanceRole": "TASK",
                    "InstanceType": task_instance_type,
                    "Market": task_instance_market.name,
                    "InstanceCount": task_instance_count,
                    "EbsConfiguration": {
                        "EbsBlockDeviceConfigs": [
                            {
                                "VolumeSpecification": {
                                    "SizeInGB": task_instance_ebs_size,
                                    "VolumeType": "io1",
                                    "Iops": task_instance_ebs_size * 50,
                                },
                                "VolumesPerInstance": 1,
                            }
                        ],
                        "EbsOptimized": True,
                    },
                }
            )
            overrides["TaskInstanceCount"] = {
                "JsonPath": "Instances.InstanceGroups.2.InstanceCount",
                "Default": task_instance_count,
            }
            overrides["TaskInstanceType"] = {
                "JsonPath": "Instances.InstanceGroups.2.InstanceType",
                "Default": task_instance_type,
            }
            overrides["TaskInstanceMarket"] = {
                "JsonPath": "Instances.InstanceGroups.2.Market",
                "Default": task_instance_market.value,
            }

        self.override_interfaces["default"].update(overrides)
        self.update_config(config)
