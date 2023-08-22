# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Optional

import aws_cdk.aws_cloud9 as cloud9
from aws_cdk import Stack
from constructs import Construct


class Cloud9Stack(Stack):  # type: ignore
    """
    Creates a Cloud9 instance

    Parameters
    ----------
    Stack : Stack
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        connection_type: Optional[str],
        image_id: Optional[str],
        instance_stop_time_minutes: Optional[int],
        instance_type: str,
        name: Optional[str],
        owner_arn: str,
        subnet_id: str,
        **kwargs: Any,
    ) -> None:
        """_summary_

        _extended_summary_

        Parameters
        ----------
        scope : Construct
            The construct's parent
        id : str
            The unique identifier of the resource
        connection_type: str
            The connection type used for connecting to an Amazon EC2 environment.
            Valid values are CONNECT_SSM (default) and CONNECT_SSH
        image_id : str
            The identifier for the Amazon Machine Image (AMI) that's used to create
            the EC2 instance. To choose an AMI for the instance, you must specify a
            valid AMI alias or a valid AWS Systems Manager path.
        instance_stop_time_minutes : int
            The number of minutes until the running instance is shut down after the
            environment was last used
        instance_type : str
            Type of instance to launch
        name : str
            The name of the Cloud9 instance
        owner_arn : str
            The Amazon Resource Name (ARN) of the environment owner. This ARN can be the
            ARN of any AWS Identity and Access Management principal. If this value is
            not specified, the ARN defaults to this environment's creator.
        subnet_id : str
            The ID of the subnet in Amazon Virtual Private Cloud (Amazon VPC) that AWS
            Cloud9 will use to communicate with the Amazon Elastic Compute Cloud
            (Amazon EC2) instance
        """
        super().__init__(scope, id, description="This stack deploys Networking resources for ADDF", **kwargs)

        self.cloud9_instance = cloud9.CfnEnvironmentEC2(
            self,
            "Cloud9Env",
            instance_type=instance_type,
            owner_arn=owner_arn,
            subnet_id=subnet_id,
            # the properties below are optional
            image_id=image_id,
            automatic_stop_time_minutes=instance_stop_time_minutes,
            connection_type=connection_type,
            name=name,
        )
