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

import logging
from typing import Any, List, Optional, cast

import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_fsx as fsx
from aws_cdk import Aspects, CfnTag, Stack, Tags
from cdk_nag import AwsSolutionsChecks, NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class FsxFileSystem(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment_name: str,
        module_name: str,
        vpc_id: str,
        private_subnet_ids: List[str],
        raw_bucket_name: Optional[str],
        interm_bucket_name: Optional[str],
        curated_bucket_name: Optional[str],
        **kwargs: Any,
    ) -> None:
        # ADDL Env vars
        self.deployment_name = deployment_name
        self.module_name = module_name

        super().__init__(scope, id, **kwargs)
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{deployment_name}")

        self.vpc_id = vpc_id
        self.vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=vpc_id,
        )

        self.private_subnets = []
        self.private_subnet_ids = []
        # subnet id needs to be list
        for idx, subnet_id in enumerate(private_subnet_ids):
            self.private_subnets.append(ec2.Subnet.from_subnet_id(scope=self, id=f"subnet{idx}", subnet_id=subnet_id))
            self.private_subnet_ids.append(str(subnet_id))

        self.fsx_security_group = ec2.SecurityGroup(
            self,
            "FsxSg",
            vpc=self.vpc,
            allow_all_outbound=True,
            security_group_name="fsx-lustre-sg",
        )

        self.fsx_security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(988),
            description="FSx Lustre",
        )

        self.fsx_filesystem = fsx.CfnFileSystem(
            self,
            "Fsx",
            file_system_type="LUSTRE",
            storage_capacity=1200,
            subnet_ids=[self.private_subnet_ids[0]],
            security_group_ids=[self.fsx_security_group.security_group_id],
            tags=[CfnTag(key="Name", value="fsx-lustre")],
            lustre_configuration=fsx.CfnFileSystem.LustreConfigurationProperty(
                deployment_type="PERSISTENT_2",
                per_unit_storage_throughput=250,
                data_compression_type="LZ4",
            ),
        )

        # print("Mount Values")
        # for bucket_name in [raw_bucket_name, interm_bucket_name, curated_bucket_name]:
        #     print(f"Running data create-data-repository-association for bucket `{bucket_name}`")
        #     data_repo_ass_cmd = f"aws fsx create-data-repository-association
        #           --file-system-id {self.fsx_filesystem.ref}
        #           --file-system-path /ns1/{bucket_name}/
        #           --data-repository-path s3://{bucket_name}/"
        #     print(os.popen(data_repo_ass_cmd).read())

        Aspects.of(self).add(AwsSolutionsChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            apply_to_nested_stacks=True,
            suppressions=[
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Managed Policies are for service account roles only",
                    "applies_to": "*",
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Resource access restriced to ADDF resources",
                    "applies_to": "*",
                },
            ],
        )
