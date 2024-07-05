# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from typing import Any, cast

import cdk_nag
from aws_cdk import Aspects, Duration, Stack, Tags, aws_eks, aws_iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk.lambda_layer_kubectl_v29 import KubectlV29Layer
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class TrainingPipeline(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        project_name: str,
        deployment_name: str,
        module_name: str,
        eks_cluster_name: str,
        eks_admin_role_arn: str,
        eks_handler_rolearn: str,
        eks_openid_connect_provider_arn: str,
        eks_cluster_endpoint: str,
        eks_cert_auth_data: str,
        training_namespace_name: str,
        training_image_uri: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            scope,
            id,
            **kwargs,
        )

        dep_mod = f"{project_name}-{deployment_name}-{module_name}"
        dep_mod = dep_mod[0:19]
        # used to tag AWS resources. Tag Value length cant exceed 256 characters
        full_dep_mod = dep_mod[:256] if len(dep_mod) > 256 else dep_mod
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=full_dep_mod)

        policy_statements = [
            aws_iam.PolicyStatement(
                actions=["ecr:*"],
                effect=aws_iam.Effect.ALLOW,
                resources=[
                    f"arn:aws:ecr:{self.region}:{self.account}:repository/{project_name}-{deployment_name}-{module_name}*"
                ],
            ),
        ]

        handler_role = aws_iam.Role.from_role_arn(
            self, "HandlerRole", eks_handler_rolearn
        )

        provider = aws_eks.OpenIdConnectProvider.from_open_id_connect_provider_arn(
            self, "Provider", eks_openid_connect_provider_arn
        )
        cluster = aws_eks.Cluster.from_cluster_attributes(
            self,
            f"eks-{deployment_name}-{module_name}",
            cluster_name=eks_cluster_name,
            open_id_connect_provider=provider,
            kubectl_role_arn=eks_admin_role_arn,
            kubectl_lambda_role=handler_role,
            kubectl_layer=KubectlV29Layer(self, "Kubectlv29Layer"),
        )

        namespace = aws_eks.KubernetesManifest(
            self,
            "namespace",
            cluster=cluster,
            manifest=[
                {
                    "apiVersion": "v1",
                    "kind": "Namespace",
                    "metadata": {"name": training_namespace_name},
                }
            ],
            overwrite=True,  # Create if not exists
        )

        service_account = cluster.add_service_account(
            "service-account", name=module_name, namespace=training_namespace_name
        )
        service_account.node.add_dependency(namespace)
        service_account_role: aws_iam.Role = cast(aws_iam.Role, service_account.role)
        if service_account_role.assume_role_policy:
            service_account_role.assume_role_policy.add_statements(
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=["sts:AssumeRole"],
                    principals=[aws_iam.ServicePrincipal("states.amazonaws.com")],
                )
            )
        for statement in policy_statements:
            service_account_role.add_to_policy(statement=statement)

        rbac_role = cluster.add_manifest(
            "rbac-role",
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "Role",
                "metadata": {
                    "name": "module-owner",
                    "namespace": training_namespace_name,
                },
                "rules": [{"apiGroups": ["*"], "resources": ["*"], "verbs": ["*"]}],
            },
        )
        rbac_role.node.add_dependency(namespace)

        rbac_role_binding = cluster.add_manifest(
            "rbac-role-binding",
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "RoleBinding",
                "metadata": {"name": module_name, "namespace": training_namespace_name},
                "roleRef": {
                    "apiGroup": "rbac.authorization.k8s.io",
                    "kind": "Role",
                    "name": "module-owner",
                },
                "subjects": [
                    {"kind": "User", "name": f"{project_name}-{module_name}"},
                    {
                        "kind": "ServiceAccount",
                        "name": module_name,
                        "namespace": training_namespace_name,
                    },
                ],
            },
        )
        rbac_role_binding.node.add_dependency(service_account)

        rbac_role = cluster.add_manifest(
            "rbac-role-default",
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "Role",
                "metadata": {"name": "default-access", "namespace": "default"},
                "rules": [
                    {
                        "apiGroups": ["*"],
                        "resources": ["*"],
                        "verbs": ["get", "list", "watch"],
                    }
                ],
            },
        )
        rbac_role.node.add_dependency(namespace)

        rbac_role_binding = cluster.add_manifest(
            "rbac-role-binding-default",
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "RoleBinding",
                "metadata": {"name": "default-access", "namespace": "default"},
                "roleRef": {
                    "apiGroup": "rbac.authorization.k8s.io",
                    "kind": "Role",
                    "name": "default-access",
                },
                "subjects": [
                    {"kind": "User", "name": f"{project_name}-{module_name}"},
                    {
                        "kind": "ServiceAccount",
                        "name": module_name,
                        "namespace": training_namespace_name,
                    },
                ],
            },
        )
        rbac_role_binding.node.add_dependency(service_account)

        rbac_cluster_role_binding = cluster.add_manifest(
            "rbac-cluster-role-binding",
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "ClusterRoleBinding",
                "metadata": {"name": f"system-access-{module_name}"},
                "roleRef": {
                    "apiGroup": "rbac.authorization.k8s.io",
                    "kind": "ClusterRole",
                    "name": "system-access",
                },
                "subjects": [
                    {"kind": "User", "name": f"{project_name}-{module_name}"},
                    {
                        "kind": "ServiceAccount",
                        "name": module_name,
                        "namespace": training_namespace_name,
                    },
                ],
            },
        )
        rbac_cluster_role_binding.node.add_dependency(service_account)

        self.eks_service_account_role = service_account.role

        _final_status = sfn.Pass(self, "final step")  # noqa: F841

        # States language JSON to put an item into DynamoDB
        # snippet generated from
        # https://docs.aws.amazon.com/step-functions/latest/dg/tutorial-code-snippet.html#tutorial-code-snippet-1
        body = {
            "apiVerson": "batch/v1",
            "kind": "Job",
            "metadata": {
                "namespace": training_namespace_name,
                "name.$": "States.Format('pytorch-training-{}', $$.Execution.Name)",
            },
            "spec": {
                "backoffLimit": 1,
                "template": {
                    "spec": {
                        "restartPolicy": "OnFailure",
                        "serviceAccountName": module_name,
                        "containers": [
                            {
                                "name": "pytorch",
                                "image": training_image_uri,
                                "imagePullPolicy": "Always",
                                "volumeMounts": [
                                    {
                                        "name": "persistent-storage",
                                        "mountPath": "/data",
                                    }
                                ],
                                "command": [
                                    "python3",
                                    "/aws/pytorch-mnist/mnist.py",
                                    "--epochs=1",
                                    "--save-model",
                                ],
                                "env": [
                                    {
                                        "name": "TRAINING_JOB_ID",
                                        "value.$": "States.Format('pytorch-training-{}', $$.Execution.Name)",
                                    }
                                ],
                                # "resources": {"limits": {"nvidia.com/gpu": 1}},
                            }
                        ],
                        "nodeSelector": {"usage": "gpu"},
                        "volumes": [
                            {
                                "name": "persistent-storage",
                                "persistentVolumeClaim": {
                                    "claimName": os.getenv(
                                        "SEEDFARMER_PARAMETER_PVC_NAME"
                                    )
                                },
                            }
                        ],
                    },
                },
            },
        }

        state_json = {
            "Type": "Task",
            "Resource": "arn:aws:states:::eks:runJob.sync",
            "Parameters": {
                "ClusterName": eks_cluster_name,
                "Namespace": training_namespace_name,
                "CertificateAuthority": eks_cert_auth_data,
                "Endpoint": eks_cluster_endpoint,
                "LogOptions": {"RetrieveLogs": True},
                "Job": body,
            },
        }

        # custom state which represents a task to insert data into DynamoDB
        custom = sfn.CustomState(self, "eks-training", state_json=state_json)

        log_group = logs.LogGroup(self, "TrainingOnEKSLogGroup")

        sm = sfn.StateMachine(  # noqa: F841
            self,
            "TrainingOnEKS",
            definition_body=sfn.DefinitionBody.from_chainable(sfn.Chain.start(custom)),
            timeout=Duration.minutes(15),
            logs=sfn.LogOptions(destination=log_group, level=sfn.LogLevel.ALL),
            role=service_account.role,
        )

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            apply_to_nested_stacks=True,
            suppressions=[
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-IAM4",
                        "reason": "Managed Policies are for service account roles only",
                    }
                ),
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-IAM5",
                        "reason": "Resource access restriced to project resources",
                    }
                ),
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-SF2",
                        "reason": "Xray disabled",
                    }
                ),
            ],
        )
