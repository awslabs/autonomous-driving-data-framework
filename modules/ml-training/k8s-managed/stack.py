# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, cast
import boto3
import os
import cdk_nag
from aws_cdk import Aspects, Stack, Tags, aws_eks, aws_iam, Duration
from aws_cdk import aws_stepfunctions as sfn

from aws_cdk import aws_logs as logs
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class TrainingDags(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment_name: str,
        module_name: str,
        eks_cluster_name: str,
        eks_admin_role_arn: str,
        eks_openid_connect_provider_arn: str,
        **kwargs: Any,
    ) -> None:
        # ADDF Env vars
        self.deployment_name = deployment_name
        self.module_name = module_name

        super().__init__(
            scope,
            id,
            description="(SO9154) Autonomous Driving Data Framework (ADDF) - k8s-managed",
            **kwargs,
        )
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{deployment_name}")

        # Create Dag IAM Role and policy
        policy_statements = [
            aws_iam.PolicyStatement(
                actions=["sqs:*"],
                effect=aws_iam.Effect.ALLOW,
                resources=[f"arn:aws:sqs:{self.region}:{self.account}:addf-{deployment_name}-{module_name}*"],
            ),
            aws_iam.PolicyStatement(
                actions=["ecr:*"],
                effect=aws_iam.Effect.ALLOW,
                resources=[
                    f"arn:aws:ecr:{self.region}:{self.account}:repository/addf-{deployment_name}-{module_name}*"
                ],
            ),
        ]
        
        provider = aws_eks.OpenIdConnectProvider.from_open_id_connect_provider_arn(
            self, "Provider", eks_openid_connect_provider_arn
        )
        cluster = aws_eks.Cluster.from_cluster_attributes(
            self,
            f"eks-{self.deployment_name}-{self.module_name}",
            cluster_name=eks_cluster_name,
            open_id_connect_provider=provider,
            kubectl_role_arn=eks_admin_role_arn,
        )

        namespace = cluster.add_manifest(
            "namespace",
            {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {"name": module_name},
            },
        )

        service_account = cluster.add_service_account("service-account", name=module_name, namespace=module_name)
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
                "metadata": {"name": "module-owner", "namespace": module_name},
                "rules": [{"apiGroups": ["*"], "resources": ["*"], "verbs": ["*"]}],
            },
        )
        rbac_role.node.add_dependency(namespace)

        rbac_role_binding = cluster.add_manifest(
            "rbac-role-binding",
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "RoleBinding",
                "metadata": {"name": module_name, "namespace": module_name},
                "roleRef": {
                    "apiGroup": "rbac.authorization.k8s.io",
                    "kind": "Role",
                    "name": "module-owner",
                },
                "subjects": [
                    {"kind": "User", "name": f"addf-{module_name}"},
                    {
                        "kind": "ServiceAccount",
                        "name": module_name,
                        "namespace": module_name,
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
                    {"kind": "User", "name": f"addf-{module_name}"},
                    {
                        "kind": "ServiceAccount",
                        "name": module_name,
                        "namespace": module_name,
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
                    {"kind": "User", "name": f"addf-{module_name}"},
                    {
                        "kind": "ServiceAccount",
                        "name": module_name,
                        "namespace": module_name,
                    },
                ],
            },
        )
        rbac_cluster_role_binding.node.add_dependency(service_account)

        self.eks_service_account_role = service_account.role


        final_status = sfn.Pass(self, "final step")

        # States language JSON to put an item into DynamoDB
        # snippet generated from https://docs.aws.amazon.com/step-functions/latest/dg/tutorial-code-snippet.html#tutorial-code-snippet-1
        body = {
            "apiVerson": "batch/v1",
            "kind": "Job",
            "metadata": {"namespace": module_name, "name": "pytorch-training"},
            "spec": {
                "backoffLimit": 1,
                "template": {
                    "metadata": {"annotations": {"sidecar.istio.io/inject": "false"}},
                    "spec": {
                        "restartPolicy": "OnFailure",
                        "containers": [
                            {
                                "name": "pytorch",
                                "image": f'{os.getenv("REPOSITORY_URI")}:{os.getenv("IMAGE_TAG")}',
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
                                "env": [],
                                # "resources": {"limits": {"nvidia.com/gpu": 1}},
                            }
                        ],
                        "nodeSelector": {"usage": "gpu"},
                        "volumes": [
                            {
                                "name": "persistent-storage",
                                "persistentVolumeClaim": {"claimName": os.getenv('ADDF_PARAMETER_PVC_NAME')},
                            }
                        ],
                    },
                },
            },
        }
        
        client = boto3.client('eks')

        response = client.describe_cluster(
            name=eks_cluster_name
        )

        state_json = {
            "Type": "Task",
            "Resource": "arn:aws:states:::eks:runJob.sync",
            "Parameters": {
                "ClusterName": eks_cluster_name,
                "Namespace": module_name,
                "CertificateAuthority": response['cluster']['certificateAuthority']['data'],
                "Endpoint": response['cluster']['endpoint'],
                "LogOptions": {
                    "RetrieveLogs": True
                },
                "Job": body
            }
        }

        # custom state which represents a task to insert data into DynamoDB
        custom = sfn.CustomState(self, "eks-training",
            state_json=state_json
        )

        log_group = logs.LogGroup(self, "TrainingOnEKSLogGroup")
        
        sm = sfn.StateMachine(self, "TrainingOnEKS", definition_body=sfn.DefinitionBody.from_chainable(
            sfn.Chain.start(custom)
        ),
            timeout=Duration.minutes(15),
            logs=sfn.LogOptions(
                destination=log_group,
                level=sfn.LogLevel.ALL
            ),
            role=service_account.role
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
                        "reason": "Resource access restriced to ADDF resources",
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
