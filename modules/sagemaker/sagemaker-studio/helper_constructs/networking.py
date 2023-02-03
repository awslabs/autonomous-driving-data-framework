from aws_cdk import aws_ec2 as ec2
from constructs import Construct

"""
This is an optional construct to setup the Networking resources (VPC and Subnets) from existing resources in the account to be used in the CDK APP.
"""
from typing import List


class Networking(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc_id: str,
        subnet_ids: List[str],
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # vpc resource to be used for the endpoint and lambda vpc configs
        self.vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id=vpc_id)

        # subnets resources should use
        self.subnets = [
            ec2.Subnet.from_subnet_id(self, f"SUBNET-{subnet_id}", subnet_id)
            for subnet_id in subnet_ids
        ]
