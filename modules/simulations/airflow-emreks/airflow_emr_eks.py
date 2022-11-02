# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import random
from typing import List, cast

# import cdk_nag
from aws_cdk import Aspects, CfnJson, CfnOutput, Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_eks as eks
from aws_cdk import aws_emr as emr
from aws_cdk import aws_emrcontainers as emrc
from aws_cdk import aws_iam as iam

# from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

"""
This stack deploys the following:
- EMR on EKS virtual cluster
- Airflow with EMR on EKS
"""


class AirflowEmrEksStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        deployment_name: str,
        module_name: str,
        mwaa_exec_role: str,
        eks_cluster_name: str,
        emr_namespace: str,
        eks_openid_issuer: str,
        eks_admin_role_arn: str,
        eks_oidc_arn: str,
        **kwargs,
    ) -> None:
        # ADDF Env vars
        self.deployment_name = deployment_name
        self.module_name = module_name
        self.mwaa_exec_role = mwaa_exec_role
        self.emr_namespace = emr_namespace

        super().__init__(
            scope,
            id,
            description="This stack deploys a pattern where Airflow triggers EMR on EKS for ADDF",
            **kwargs,
        )
        dep_mod = f"addf-{self.deployment_name}-{self.module_name}"
        dep_mod = dep_mod[:27]

        Tags.of(scope=cast(IConstruct, self)).add(
            key="Deployment", value=f"addf-{self.deployment_name}"
        )

        # EMR virtual cluster
        self.emr_vc = emrc.CfnVirtualCluster(
            scope=self,
            id=f"{dep_mod}-EMRVirtualCluster",
            container_provider=emrc.CfnVirtualCluster.ContainerProviderProperty(
                id=eks_cluster_name,
                info=emrc.CfnVirtualCluster.ContainerInfoProperty(
                    eks_info=emrc.CfnVirtualCluster.EksInfoProperty(
                        namespace=emr_namespace
                    )
                ),
                type="EKS",
            ),
            name=f"{dep_mod}-EMROnEKSCluster",
        )

        # Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        # NagSuppressions.add_stack_suppressions(
        #     self,
        #     apply_to_nested_stacks=True,
        #     suppressions=[
        #         {
        #             "id": "AwsSolutions-IAM4",
        #             "reason": "Managed Policies are for service account roles only",
        #             "applies_to": "*",
        #         },
        #         {
        #             "id": "AwsSolutions-IAM5",
        #             "reason": "Resource access restriced to ADDF resources",
        #             "applies_to": "*",
        #         },
        #     ],
        # )
