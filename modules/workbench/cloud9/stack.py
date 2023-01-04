#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License").
#    You may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from typing import Any

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
        connection_type: str,
        image_id: str,
        instance_stop_time_minutes: int,
        instance_type: str,
        name: str,
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
            The name of the environment
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
            image_id=image_id,
            instance_type=instance_type,
            owner_arn=owner_arn,
            subnet_id=subnet_id,
            # the properties below are optional
            automatic_stop_time_minutes=instance_stop_time_minutes,
            connection_type=connection_type,
            name=name,
        )
