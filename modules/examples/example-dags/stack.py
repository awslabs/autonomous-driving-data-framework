# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Optional, cast

import aws_cdk.aws_iam as aws_iam
import cdk_nag
from aws_cdk import Aspects, Stack, Tags
from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class DagIamRole(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment_name: str,
        module_name: str,
        mwaa_exec_role: str,
        bucket_policy_arn: Optional[str] = None,
        permission_boundary_arn: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        # ADDF Env vars
        self.deployment_name = deployment_name
        self.module_name = module_name
        self.mwaa_exec_role = mwaa_exec_role

        super().__init__(scope, id, description="This stack deploys Example DAGs resources for ADDF", **kwargs)
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{deployment_name}")

        # Create Dag IAM Role and policy
        dag_statement = aws_iam.PolicyDocument(
            statements=[
                aws_iam.PolicyStatement(
                    actions=["ec2:Describe*"],
                    effect=aws_iam.Effect.ALLOW,
                    resources=["*"],
                )
            ]
        )

        managed_policies = (
            [aws_iam.ManagedPolicy.from_managed_policy_arn(self, "bucket-policy", bucket_policy_arn)]
            if bucket_policy_arn
            else []
        )

        # Role with Permission Boundary
        r_name = f"addf-{self.deployment_name}-{self.module_name}-dag-role"
        self.dag_role = aws_iam.Role(
            self,
            f"dag-role-{self.deployment_name}-{self.module_name}",
            assumed_by=aws_iam.ArnPrincipal(self.mwaa_exec_role),
            inline_policies={"DagPolicyDocument": dag_statement},
            managed_policies=managed_policies,
            permissions_boundary=aws_iam.ManagedPolicy.from_managed_policy_arn(
                self,
                f"perm-boundary-{self.deployment_name}-{self.module_name}",
                permission_boundary_arn,
            )
            if permission_boundary_arn
            else None,
            role_name=r_name,
            path="/",
        )

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            [
                {  # type: ignore
                    "id": "AwsSolutions-IAM5",
                    "reason": "Resource access restriced describe only",
                },
            ],
        )
