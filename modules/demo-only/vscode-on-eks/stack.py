# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, cast

import aws_cdk
import aws_cdk.aws_s3_assets as s3_assets
import cdk_nag
from aws_cdk import Aspects, Stack, Tags
from aws_cdk import aws_eks as eks
from aws_cdk import aws_iam as iam
from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class VSCodeOnEKS(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment: str,
        module: str,
        eks_cluster_name: str,
        eks_admin_role_arn: str,
        eks_oidc_arn: str,
        vscode_password: str,
        **kwargs: Any,
    ) -> None:

        super().__init__(
            scope,
            id,
            description="This stack deploys VSCode environment for ADDF",
            **kwargs,
        )
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{deployment}")

        dep_mod = f"addf-{deployment}-{module}"
        # CDK Env Vars
        account: str = aws_cdk.Aws.ACCOUNT_ID
        region: str = aws_cdk.Aws.REGION
        NAMESPACE = "code-server"

        # Import EKS Cluster
        provider = eks.OpenIdConnectProvider.from_open_id_connect_provider_arn(
            self, f"{dep_mod}-provider", eks_oidc_arn
        )
        eks_cluster = eks.Cluster.from_cluster_attributes(
            self,
            f"{dep_mod}-eks-cluster",
            cluster_name=eks_cluster_name,
            kubectl_role_arn=eks_admin_role_arn,
            open_id_connect_provider=provider,
        )

        vscode_on_eks_policy_statements = [
            iam.PolicyStatement(
                actions=[
                    "es:ESGet*",
                ],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:es:{region}:{account}:domain/*"],
            ),
            iam.PolicyStatement(
                actions=[
                    "s3:List*",
                    "states:List*",
                    "cloudformation:List*",
                    "lambda:List*",
                    "logs:List*",
                    "ssm:List*",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=[
                    "cloudformation:ListStackSetOperations",
                    "cloudformation:ListStackInstances",
                    "cloudformation:ListStackSets",
                    "cloudformation:DescribeStacks",
                    "cloudformation:ListStackSetOperationResults",
                    "cloudformation:ListChangeSets",
                    "cloudformation:ListStackResources",
                    "states:DescribeStateMachineForExecution",
                    "states:DescribeActivity",
                    "states:StopExecution",
                    "states:DescribeStateMachine",
                    "states:ListExecutions",
                    "states:DescribeExecution",
                    "states:GetExecutionHistory",
                    "states:StartExecution",
                    "states:ListTagsForResource",
                    "s3:GetObjectTagging",
                    "s3:ListBucket",
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:GetObjectVersion",
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:aws:states:{region}:{account}:execution:*:*",
                    f"arn:aws:states:{region}:{account}:stateMachine:*",
                    f"arn:aws:states:{region}:{account}:activity:*",
                    f"arn:aws:cloudformation:{region}:{account}:stackset/addf*:*",
                    f"arn:aws:cloudformation:{region}:{account}:stack/addf*/*",
                    "arn:aws:s3:::addf*",
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogStream",
                    "logs:CreateLogGroup",
                    "logs:PutLogEvents",
                    "logs:GetLogEvents",
                    "logs:GetLogRecord",
                    "logs:GetLogGroupFields",
                    "logs:GetQueryResults",
                    "logs:DescribeLogGroups",
                ],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:logs:{region}:{account}:log-group:*"],
            ),
            iam.PolicyStatement(
                actions=[
                    "lambda:List*",
                    "lambda:Get*",
                    "cloudformation:List*",
                    "cloudformation:Describe*",
                    "states:Describe*",
                    "states:List*",
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    f"arn:aws:cloudformation:{region}:{account}:stackset/addf*:*",
                    f"arn:aws:cloudformation:{region}:{account}:stack/addf-/*",
                    f"arn:aws:lambda:{region}:{account}:function:addf-",
                    f"arn:aws:states:{region}:{account}:execution:*:*",
                    f"arn:aws:states:{region}:{account}:stateMachine:*",
                    f"arn:aws:states:{region}:{account}:activity:*",
                ],
            ),
            iam.PolicyStatement(
                actions=["sts:AssumeRole"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:iam::{account}:role/addf-*"],
            ),
        ]

        vscode_policy = iam.Policy(
            self,
            "vscodepolicy",
            statements=vscode_on_eks_policy_statements,
        )

        # Create jupyter-hub namespace
        vscode_namespace = eks_cluster.add_manifest(
            "code-server-namespace",
            {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {"name": NAMESPACE},
            },
        )

        vscode_service_account = eks_cluster.add_service_account("vscode", name="vscode", namespace=NAMESPACE)

        vscode_service_account.role.attach_inline_policy(vscode_policy)

        chart_asset = s3_assets.Asset(
            self,
            "VSCodeChartAsset",
            path="./helm-chart",
        )

        vscode_chart = eks_cluster.add_helm_chart(
            "vscode-chart",
            chart_asset=chart_asset,
            create_namespace=True,
            namespace=NAMESPACE,
            values={
                "namespace": NAMESPACE,
                "proxy": {"service": {"type": "NodePort"}},
                "ingress": {
                    "annotations": {
                        "kubernetes.io/ingress.class": "alb",
                        "alb.ingress.kubernetes.io/scheme": "internet-facing",
                        "alb.ingress.kubernetes.io/success-codes": "200,302",
                    },
                },
                "vscode": {
                    "password": vscode_password,
                },
                "serviceAccountName": "vscode",
            },
        )

        vscode_service_account.node.add_dependency(vscode_namespace)
        vscode_chart.node.add_dependency(vscode_service_account)

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            apply_to_nested_stacks=True,
            suppressions=[
                {  # type: ignore
                    "id": "AwsSolutions-IAM4",
                    "reason": "Managed Policies are for service account roles only",
                },
                {  # type: ignore
                    "id": "AwsSolutions-IAM5",
                    "reason": "Resource access restriced to ADDF resources",
                },
            ],
        )
