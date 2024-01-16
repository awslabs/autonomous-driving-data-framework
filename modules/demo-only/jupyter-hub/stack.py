# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
from typing import Any, cast

import cdk_nag
from aws_cdk import Aspects, Stack, Tags
from aws_cdk import aws_eks as eks
from aws_cdk import aws_iam as iam
from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)

project_dir = os.path.dirname(os.path.abspath(__file__))


class JupyterHubStack(Stack):
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
        jh_username: str,
        jh_password: str,
        jh_image_name: str,
        jh_image_tag: str,
        **kwargs: Any,
    ) -> None:

        super().__init__(
            scope,
            id,
            description="This stack deploys Self managed JupyterHub environment for ADDF",
            **kwargs,
        )
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{deployment}")

        dep_mod = f"addf-{deployment}-{module}"

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

        # Create jupyter-hub namespace
        jupyter_hub_namespace = eks_cluster.add_manifest(
            "jupyter-hub-namespace",
            {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {"name": "jupyter-hub"},
            },
        )

        jupyterhub_service_account = eks_cluster.add_service_account(
            "jupyterhub", name="jupyterhub", namespace="jupyter-hub"
        )

        jupyterhub_policy_statement_json_path = os.path.join(project_dir, "addons-iam-policies", "jupyterhub-iam.json")
        with open(jupyterhub_policy_statement_json_path) as json_file:
            jupyterhub_policy_statement_json = json.load(json_file)

        # Attach the necessary permissions
        jupyterhub_policy = iam.Policy(
            self,
            "jupyterhubpolicy",
            document=iam.PolicyDocument.from_json(jupyterhub_policy_statement_json),
        )
        jupyterhub_service_account.role.attach_inline_policy(jupyterhub_policy)

        k8s_values = {
            "proxy": {"service": {"type": "NodePort"}},
            "scheduling": {
                "podPriority": {"enabled": True},
                "userPlaceholder": {"replicas": 3},
            },
            "singleuser": {
                "startTimeout": 300,
                "storage": {"capacity": "4Gi", "dynamic": {"storageClass": "gp2"}},
                "serviceAccountName": "jupyterhub",
            },
            "ingress": {
                "annotations": {
                    "ingress.kubernetes.io/proxy-body-size": "64m",
                    "kubernetes.io/ingress.class": "alb",
                    "alb.ingress.kubernetes.io/scheme": "internet-facing",
                    "alb.ingress.kubernetes.io/success-codes": "200,302",
                },
                "enabled": True,
                "pathType": "Prefix",
            },
            "hub": {
                "baseUrl": "/jupyter",
                "config": {
                    "DummyAuthenticator": {"password": jh_password},
                    "JupyterHub": {"authenticator_class": "dummy"},
                    "Authenticator": {"allowed_users": [jh_username]},
                },
            },
        }
        if jh_image_name and jh_image_tag:
            k8s_values["singleuser"]["image"] = {  # type: ignore
                "name": jh_image_name,
                "tag": jh_image_tag,
                "pullPolicy": "Always",
            }

        jupyterhub_chart = eks_cluster.add_helm_chart(
            "jupyterhub-chart",
            chart="jupyterhub",
            release="jupyterhub",
            repository="https://jupyterhub.github.io/helm-chart",
            create_namespace=True,
            namespace="jupyter-hub",
            values=k8s_values,
        )

        jupyterhub_service_account.node.add_dependency(jupyter_hub_namespace)
        jupyterhub_chart.node.add_dependency(jupyterhub_service_account)

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
