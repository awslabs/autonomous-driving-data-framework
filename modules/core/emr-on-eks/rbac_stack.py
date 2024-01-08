# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# type: ignore

import logging
from typing import Any, cast

# import cdk_nag
from aws_cdk import CfnJson, Stack, Tags
from aws_cdk import aws_eks as eks
from aws_cdk import aws_iam as iam

# from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)

"""
This stack deploys the following:
- EKS RBAC configuration to support EMR on EKS
"""


class EmronEksRbacStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment_name: str,
        module_name: str,
        mwaa_exec_role: str,
        eks_cluster_name: str,
        eks_admin_role_arn: str,
        eks_oidc_arn: str,
        eks_openid_issuer: str,
        emr_namespace: str,
        raw_bucket_name: str,
        artifact_bucket_name: str,
        logs_bucket_name: str,
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
            description="This stack deploys EMR on EKS RBAC Configuration for ADDF",
            **kwargs,
        )
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{self.deployment_name}")

        dep_mod = f"addf-{self.deployment_name}-{self.module_name}"
        dep_mod = dep_mod[:27]

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

        self.emrsvcrolearn = f"arn:aws:iam::{self.account}:role/AWSServiceRoleForAmazonEMRContainers"

        # Create namespace for EMR to use
        namespace = eks_cluster.add_manifest(
            self.emr_namespace,
            {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {"name": self.emr_namespace},
            },
        )

        # Create k8s role for EMR
        emrrole = eks_cluster.add_manifest(
            "emrrole",
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "Role",
                "metadata": {"name": "emr-containers", "namespace": self.emr_namespace},
                "rules": [
                    {"apiGroups": [""], "resources": ["namespaces"], "verbs": ["get"]},
                    {
                        "apiGroups": [""],
                        "resources": [
                            "serviceaccounts",
                            "services",
                            "configmaps",
                            "events",
                            "pods",
                            "pods/log",
                        ],
                        "verbs": [
                            "get",
                            "list",
                            "watch",
                            "describe",
                            "create",
                            "edit",
                            "delete",
                            "deletecollection",
                            "annotate",
                            "patch",
                            "label",
                        ],
                    },
                    {
                        "apiGroups": [""],
                        "resources": ["secrets"],
                        "verbs": ["create", "patch", "delete", "watch"],
                    },
                    {
                        "apiGroups": ["apps"],
                        "resources": ["statefulsets", "deployments"],
                        "verbs": [
                            "get",
                            "list",
                            "watch",
                            "describe",
                            "create",
                            "edit",
                            "delete",
                            "annotate",
                            "patch",
                            "label",
                        ],
                    },
                    {
                        "apiGroups": ["batch"],
                        "resources": ["jobs"],
                        "verbs": [
                            "get",
                            "list",
                            "watch",
                            "describe",
                            "create",
                            "edit",
                            "delete",
                            "annotate",
                            "patch",
                            "label",
                        ],
                    },
                    {
                        "apiGroups": ["extensions"],
                        "resources": ["ingresses"],
                        "verbs": [
                            "get",
                            "list",
                            "watch",
                            "describe",
                            "create",
                            "edit",
                            "delete",
                            "annotate",
                            "patch",
                            "label",
                        ],
                    },
                    {
                        "apiGroups": ["rbac.authorization.k8s.io"],
                        "resources": ["roles", "rolebindings"],
                        "verbs": [
                            "get",
                            "list",
                            "watch",
                            "describe",
                            "create",
                            "edit",
                            "delete",
                            "deletecollection",
                            "annotate",
                            "patch",
                            "label",
                        ],
                    },
                ],
            },
        )
        emrrole.node.add_dependency(namespace)

        # Bind K8s role to user
        emrrolebind = eks_cluster.add_manifest(
            "emrrolebind",
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "RoleBinding",
                "metadata": {"name": "emr-containers", "namespace": self.emr_namespace},
                "subjects": [
                    {
                        "kind": "User",
                        "name": "emr-containers",
                        "apiGroup": "rbac.authorization.k8s.io",
                    }
                ],
                "roleRef": {
                    "kind": "Role",
                    "name": "emr-containers",
                    "apiGroup": "rbac.authorization.k8s.io",
                },
            },
        )
        emrrolebind.node.add_dependency(emrrole)

        # Job execution role
        # Ref: https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/creating-job-execution-role.html
        self.job_role = iam.Role(
            self,
            f"{dep_mod}-EMR_EKS_Job_Role",
            assumed_by=iam.ServicePrincipal("elasticmapreduce.amazonaws.com"),
        )

        self.job_role.add_to_policy(
            iam.PolicyStatement(
                resources=[
                    f"arn:aws:s3:::{logs_bucket_name}",
                    f"arn:aws:s3:::{logs_bucket_name}/*",
                    f"arn:aws:kms:{self.region}:{self.account}:key/*",
                ],
                actions=[
                    "s3:PutObject*",
                    "s3:GetObject*",
                    "s3:ListBucket",
                    "kms:Decrypt",
                    "kms:GenerateDataKey",
                ],
                effect=iam.Effect.ALLOW,
            )
        )

        self.job_role.add_to_policy(
            iam.PolicyStatement(
                resources=[f"arn:aws:logs:{self.region}:{self.account}:*"],
                actions=[
                    "logs:PutLogEvents",
                    "logs:CreateLogStream",
                    "logs:DescribeLogGroups",
                    "logs:DescribeLogStreams",
                ],
                effect=iam.Effect.ALLOW,
            )
        )

        # Modify trust policy
        string_like = CfnJson(
            self,
            "ConditionJson",
            value={
                f"{eks_openid_issuer}:sub": f"system:serviceaccount:{self.emr_namespace}:emr-containers-sa-*-*-{self.account}-*"  # noqa: E501
            },
        )
        self.job_role.assume_role_policy.add_statements(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sts:AssumeRoleWithWebIdentity"],
                principals=[
                    iam.OpenIdConnectPrincipal(
                        eks_cluster.open_id_connect_provider,
                        conditions={"StringLike": string_like},
                    )
                ],
            )
        )
        string_aud = CfnJson(
            self,
            "ConditionJsonAud",
            value={f"{eks_openid_issuer}:aud": "sts.amazon.com"},
        )
        self.job_role.assume_role_policy.add_statements(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sts:AssumeRoleWithWebIdentity"],
                principals=[
                    iam.OpenIdConnectPrincipal(
                        eks_cluster.open_id_connect_provider,
                        conditions={"StringEquals": string_aud},
                    )
                ],
            )
        )
