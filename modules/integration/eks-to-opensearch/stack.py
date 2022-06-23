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
from typing import Any, cast

import cdk_nag
from aws_cdk import Aspects, Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_eks as eks
from aws_cdk import aws_iam as iam
from aws_cdk import aws_opensearchservice as opensearch
from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class EksOpenSearchIntegrationStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment: str,
        module: str,
        opensearch_sg_id: str,
        opensearch_domain_endpoint: str,
        eks_cluster_name: str,
        eks_admin_role_arn: str,
        eks_cluster_sg_id: str,
        eks_oidc_arn: str,
        **kwargs: Any,
    ) -> None:

        super().__init__(scope, id, **kwargs)
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{deployment}")

        dep_mod = f"addf-{deployment}-{module}"
        dep_mod = dep_mod[:27]

        # Import OpenSearch Domain
        os_domain = opensearch.Domain.from_domain_endpoint(
            self, f"{dep_mod}-os-domain", f"https://{opensearch_domain_endpoint}"
        )
        os_security_group = ec2.SecurityGroup.from_security_group_id(self, f"{dep_mod}-os-sg", opensearch_sg_id)

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
        eks_cluster_security_group = ec2.SecurityGroup.from_security_group_id(
            self, f"{dep_mod}-eks-sg", eks_cluster_sg_id
        )

        # Add a rule to allow our new SG to talk to the EKS control plane
        eks_cluster_security_group.add_ingress_rule(os_security_group, ec2.Port.all_traffic())
        # Add a rule to allow the EKS control plane to talk to OS SG
        os_security_group.add_ingress_rule(eks_cluster_security_group, ec2.Port.all_traffic())

        # Create the Service Account
        fluentbit_service_account = eks_cluster.add_service_account(
            "fluentbit", name="fluentbit", namespace="kube-system"
        )

        fluentbit_policy_statement_json_1 = {"Effect": "Allow", "Action": ["es:*"], "Resource": [os_domain.domain_arn]}

        # Add the policies to the service account
        fluentbit_service_account.add_to_principal_policy(
            iam.PolicyStatement.from_json(fluentbit_policy_statement_json_1)
        )
        os_domain.grant_write(fluentbit_service_account)

        # For more info check out https://github.com/fluent/helm-charts/tree/main/charts/fluent-bit
        fluentbit_chart = eks_cluster.add_helm_chart(
            "fluentbit",
            chart="fluent-bit",
            version="0.19.17",
            release="fluent-bit",
            repository="https://fluent.github.io/helm-charts",
            namespace="kube-system",
            values={
                "serviceAccount": {"create": False, "name": "fluentbit"},
                "config": {
                    "outputs": "[OUTPUT]\n    Name            es\n    Match           *\n"
                    "    AWS_Region      " + self.region + "\n    AWS_Auth        On\n"
                    "    Host            " + os_domain.domain_endpoint + "\n    Port            443\n"
                    "    TLS             On\n    Replace_Dots    On\n    Logstash_Format    On"
                },
            },
        )
        fluentbit_chart.node.add_dependency(fluentbit_service_account)

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

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
