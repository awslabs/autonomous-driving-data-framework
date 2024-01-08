# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any, cast

# import cdk_nag
from aws_cdk import Stack, Tags
from aws_cdk import aws_emrcontainers as emrc

# from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct


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
        **kwargs: Any,
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

        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{self.deployment_name}")

        # EMR virtual cluster
        self.emr_vc = emrc.CfnVirtualCluster(
            scope=self,
            id=f"{dep_mod}-EMRVirtualCluster",
            container_provider=emrc.CfnVirtualCluster.ContainerProviderProperty(
                id=eks_cluster_name,
                info=emrc.CfnVirtualCluster.ContainerInfoProperty(
                    eks_info=emrc.CfnVirtualCluster.EksInfoProperty(namespace=emr_namespace)
                ),
                type="EKS",
            ),
            name=f"{dep_mod}-EMROnEKSCluster",
        )
