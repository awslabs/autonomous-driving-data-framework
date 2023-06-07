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

import json
import logging
import os
from typing import Any, Dict, cast

import cdk_nag
import yaml
from aws_cdk import Aspects, RemovalPolicy, Stack, Tags
from aws_cdk import aws_aps as aps
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_efs as efs
from aws_cdk import aws_eks as eks
from aws_cdk import aws_iam as iam
from aws_cdk.lambda_layer_kubectl_v23 import KubectlV23Layer
from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)

project_dir = os.path.dirname(os.path.abspath(__file__))


ALB_CONTROLLER_VERSION = "alb_contoller_version"
FSX_DRIVER_VERSION = "fsx_driver_version"
version_mappings = {
    "1.21": {ALB_CONTROLLER_VERSION: "1.3.3", FSX_DRIVER_VERSION: "1.5.0"},
    "1.22": {ALB_CONTROLLER_VERSION: "1.4.5", FSX_DRIVER_VERSION: "1.5.0"},
    "1.23": {ALB_CONTROLLER_VERSION: "1.4.5", FSX_DRIVER_VERSION: "1.5.0"},
    "default": {ALB_CONTROLLER_VERSION: "1.3.3", FSX_DRIVER_VERSION: "1.5.0"},
}


def get_version(eks_version: str, controller_name) -> str:
    if version_mappings.get(eks_version) and version_mappings[eks_version].get(controller_name):
        return version_mappings[eks_version][controller_name]
    else:
        return version_mappings["default"][controller_name]


class Eks(Stack):  # type: ignore
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        config: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        super().__init__(
            scope,
            id,
            description="This stack deploys EKS Cluster, Managed Nodegroup(s) with standard plugins for ADDF",
            **kwargs,
        )

        for k, v in config.items():
            setattr(self, k, v)

        # Tagging all resources
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{self.deployment_name}")

        # Importing the VPC
        self.vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=self.vpc_id,
        )

        cluster_admin_role = iam.Role(
            self,
            "ClusterAdminRole",
            role_name=f"addf-{self.deployment_name}-{self.module_name}-{self.region}-masterrole",
            assumed_by=iam.CompositePrincipal(
                iam.AccountRootPrincipal(),
                iam.ServicePrincipal("ec2.amazonaws.com"),
            ),
        )
        cluster_admin_policy_statement_json_1 = {
            "Effect": "Allow",
            "Action": [
                "eks:DescribeCluster",
                "iam:Get*",
                "cloudformation:List*",
                "cloudformation:Describe*",
                "cloudformation:Get*",
            ],
            "Resource": "*",
        }
        cluster_admin_policy_statement_json_2 = {
            "Effect": "Allow",
            "Action": "cloudformation:*",
            "Resource": [
                f"arn:aws:cloudformation:{self.region}:{self.account}:stack/eksctl-addf-{self.deployment_name}*",
            ],
        }
        cni_metrics_role_name = f"addf-{self.deployment_name}-{self.module_name}-CNIMetricsHelperRole"
        self.cni_metrics_role_name = cni_metrics_role_name[:60]
        cluster_admin_policy_statement_json_3 = {
            "Effect": "Allow",
            "Action": ["iam:Create*", "iam:Put*", "iam:List*", "iam:Detach*", "iam:Attach*", "iam:DeleteRole"],
            "Resource": [
                f"arn:aws:iam::{self.account}:role/AmazonEKSVPCCNIMetricsHelperRole",
                f"arn:aws:iam::{self.account}:policy/AmazonEKSVPCCNIMetricsHelperPolicy",
                f"arn:aws:iam::{self.account}:role/{self.cni_metrics_role_name}",
            ],
        }
        cluster_admin_role.add_to_principal_policy(iam.PolicyStatement.from_json(cluster_admin_policy_statement_json_1))
        cluster_admin_role.add_to_principal_policy(iam.PolicyStatement.from_json(cluster_admin_policy_statement_json_2))
        cluster_admin_role.add_to_principal_policy(iam.PolicyStatement.from_json(cluster_admin_policy_statement_json_3))

        # Creates an EKS Cluster
        eks_cluster = eks.Cluster(
            self,
            "cluster",
            vpc=self.vpc,
            cluster_name=f"addf-{self.deployment_name}-{self.module_name}-cluster",
            masters_role=cluster_admin_role,
            endpoint_access=eks.EndpointAccess.PUBLIC,
            version=eks.KubernetesVersion.of(str(self.eks_compute_config["eks_version"])),
            # Work around until CDK team makes kubectl upto date https://github.com/aws/aws-cdk/issues/23376
            kubectl_layer=KubectlV23Layer(self, "Kubectlv23Layer"),
            default_capacity=0,
            cluster_logging=[
                eks.ClusterLoggingTypes.API,
                eks.ClusterLoggingTypes.AUDIT,
                eks.ClusterLoggingTypes.AUTHENTICATOR,
                eks.ClusterLoggingTypes.CONTROLLER_MANAGER,
                eks.ClusterLoggingTypes.SCHEDULER,
            ],
        )

        # Managing core-dns, kube-proxy and vpc-cni as Server Side softwares using Addons.
        # https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html
        coredns_addon = eks.CfnAddon(
            self,
            "coredns",
            addon_name="coredns",
            resolve_conflicts="OVERWRITE",
            cluster_name=eks_cluster.cluster_name,
        )

        kube_proxy_addon = eks.CfnAddon(
            self,
            "kube-proxy",
            addon_name="kube-proxy",
            resolve_conflicts="OVERWRITE",
            cluster_name=eks_cluster.cluster_name,
        )
        vpc_cni_addon = eks.CfnAddon(
            self,
            "vpc-cni",
            addon_name="vpc-cni",
            resolve_conflicts="OVERWRITE",
            cluster_name=eks_cluster.cluster_name,
        )

        coredns_addon.node.add_dependency(eks_cluster)
        kube_proxy_addon.node.add_dependency(eks_cluster)
        vpc_cni_addon.node.add_dependency(eks_cluster)

        # Add a Managed Node Group
        if self.eks_compute_config.get("eks_nodegroup_config"):
            # Spot InstanceType
            if self.eks_compute_config.get("eks_node_spot"):
                node_capacity_type = eks.CapacityType.SPOT
            # OnDemand InstanceType
            else:
                node_capacity_type = eks.CapacityType.ON_DEMAND

            for ng in self.eks_compute_config.get("eks_nodegroup_config", [{}]):
                # Parse the instance types as comma seperated list turn into instance_types[]
                instance_types_context = ng.get("eks_node_instance_types")
                instance_types = []
                for value in instance_types_context:
                    instance_type = ec2.InstanceType(value)
                    instance_types.append(instance_type)

                eks_cluster.add_nodegroup_capacity(
                    f"cluster-default-{ng}",
                    capacity_type=node_capacity_type,
                    desired_size=ng.get("eks_node_quantity"),
                    min_size=ng.get("eks_node_min_quantity"),
                    max_size=ng.get("eks_node_max_quantity"),
                    disk_size=ng.get("eks_node_disk_size"),
                    # The default in CDK is to force upgrades through even if they violate - it is safer to not do that
                    force_update=False,
                    instance_types=instance_types,
                    labels=ng.get("eks_node_labels") if ng.get("eks_node_labels") else None,
                    # release_version=self.eks_compute_config["eks_node_ami_version"],
                ).role.add_managed_policy(
                    iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
                )

        # AWS Load Balancer Controller
        if self.eks_addons_config.get("deploy_aws_lb_controller", True):
            awslbcontroller_service_account = eks_cluster.add_service_account(
                "aws-load-balancer-controller",
                name="aws-load-balancer-controller",
                namespace="kube-system",
            )

            # Create the PolicyStatements to attach to the role
            # https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json
            awslbcontroller_policy_document_path = os.path.join(
                project_dir, "addons-iam-policies", "ingress-controller.json"
            )
            with open(awslbcontroller_policy_document_path) as json_file:
                awslbcontroller_policy_document_json = json.load(json_file)
            # Attach the necessary permissions
            awslbcontroller_policy = iam.Policy(
                self,
                "awslbcontrollerpolicy",
                document=iam.PolicyDocument.from_json(awslbcontroller_policy_document_json),
            )
            awslbcontroller_service_account.role.attach_inline_policy(awslbcontroller_policy)

            # Deploy the AWS Load Balancer Controller from the AWS Helm Chart
            # For more info check out https://github.com/aws/eks-charts/tree/master/stable/aws-load-balancer-controller
            awslbcontroller_chart = eks_cluster.add_helm_chart(
                "aws-load-balancer-controller",
                chart="aws-load-balancer-controller",
                version=get_version(str(self.eks_compute_config["eks_version"]), ALB_CONTROLLER_VERSION),
                release="awslbcontroller",
                repository="https://aws.github.io/eks-charts",
                namespace="kube-system",
                values={
                    "clusterName": eks_cluster.cluster_name,
                    "region": self.region,
                    "vpcId": self.vpc_id,
                    "serviceAccount": {
                        "create": False,
                        "name": "aws-load-balancer-controller",
                    },
                    "replicaCount": 2,
                    "podDisruptionBudget": {"maxUnavailable": 1},
                    "resources": {"requests": {"cpu": "0.25", "memory": "0.5Gi"}},
                },
            )
            awslbcontroller_chart.node.add_dependency(awslbcontroller_service_account)

        # AWS EBS CSI Driver
        if self.eks_addons_config.get("deploy_aws_ebs_csi", True):
            awsebscsidriver_service_account = eks_cluster.add_service_account(
                "awsebscsidriver", name="awsebscsidriver", namespace="kube-system"
            )

            # Reference: https://github.com/kubernetes-sigs/aws-ebs-csi-driver/blob/master/docs/example-iam-policy.json
            awsebscsidriver_policy_document_json_path = os.path.join(
                project_dir, "addons-iam-policies", "ebs-csi-iam.json"
            )
            with open(awsebscsidriver_policy_document_json_path) as json_file:
                awsebscsidriver_policy_document_json = json.load(json_file)

            # Attach the necessary permissions
            awsebscsidriver_policy = iam.Policy(
                self,
                "awsebscsidriverpolicy",
                document=iam.PolicyDocument.from_json(awsebscsidriver_policy_document_json),
            )
            awsebscsidriver_service_account.role.attach_inline_policy(awsebscsidriver_policy)

            # Install the AWS EBS CSI Driver
            # https://github.com/kubernetes-sigs/aws-ebs-csi-driver/tree/master/charts/aws-ebs-csi-driver
            awsebscsi_chart = eks_cluster.add_helm_chart(
                "aws-ebs-csi-driver",
                chart="aws-ebs-csi-driver",
                version="2.6.2",
                release="awsebscsidriver",
                repository="https://kubernetes-sigs.github.io/aws-ebs-csi-driver",
                namespace="kube-system",
                values={
                    "controller": {
                        "region": self.region,
                        "serviceAccount": {"create": False, "name": "awsebscsidriver"},
                    },
                    "node": {"serviceAccount": {"create": False, "name": "awsebscsidriver"}},
                },
            )
            awsebscsi_chart.node.add_dependency(awsebscsidriver_service_account)

            # Set up the StorageClass pointing at the new CSI Driver
            # https://github.com/kubernetes-sigs/aws-ebs-csi-driver/blob/master/examples/kubernetes/dynamic-provisioning/specs/storageclass.yaml
            ebs_csi_storageclass = eks_cluster.add_manifest(
                "EBSCSIStorageClass",
                {
                    "kind": "StorageClass",
                    "apiVersion": "storage.k8s.io/v1",
                    "metadata": {"name": "ebs"},
                    "provisioner": "ebs.csi.aws.com",
                    "volumeBindingMode": "WaitForFirstConsumer",
                },
            )
            ebs_csi_storageclass.node.add_dependency(awsebscsi_chart)

        # AWS EFS CSI Driver
        if self.eks_addons_config.get("deploy_aws_efs_csi", True):
            awsefscsidriver_service_account = eks_cluster.add_service_account(
                "awsefscsidriver", name="awsefscsidriver", namespace="kube-system"
            )

            awsefscsidriver_policy_statement_json_path = os.path.join(
                project_dir, "addons-iam-policies", "efs-csi-iam.json"
            )
            with open(awsefscsidriver_policy_statement_json_path) as json_file:
                awsefscsidriver_policy_statement_json = json.load(json_file)

            # Attach the necessary permissions
            awsefscsidriver_policy = iam.Policy(
                self,
                "awsefscsidriverpolicy",
                document=iam.PolicyDocument.from_json(awsefscsidriver_policy_statement_json),
            )
            awsefscsidriver_service_account.role.attach_inline_policy(awsefscsidriver_policy)

            # Install the AWS EFS CSI Driver
            # https://github.com/kubernetes-sigs/aws-efs-csi-driver/tree/release-1.3/charts/aws-efs-csi-driver
            awsefscsi_chart = eks_cluster.add_helm_chart(
                "aws-efs-csi-driver",
                chart="aws-efs-csi-driver",
                version="2.2.3",
                release="awsefscsidriver",
                repository="https://kubernetes-sigs.github.io/aws-efs-csi-driver/",
                namespace="kube-system",
                values={
                    "controller": {
                        "serviceAccount": {"create": False, "name": "awsefscsidriver"},
                        "deleteAccessPointRootDir": True,
                    },
                    "node": {"serviceAccount": {"create": False, "name": "awsefscsidriver"}},
                },
            )
            awsefscsi_chart.node.add_dependency(awsefscsidriver_service_account)

            # Create Security Group for the EFS Filesystem
            # Create SecurityGroup for OpenSearch
            efs_security_group = ec2.SecurityGroup(self, "EFSSecurityGroup", vpc=self.vpc, allow_all_outbound=True)
            # Add a rule to allow the EKS Nodes to talk to our new EFS (will not work with SGs for Pods by default)
            efs_security_group.add_ingress_rule(eks_cluster.cluster_security_group, ec2.Port.tcp(2049))

            # Add a rule to allow our our VPC CIDR to talk to the EFS (SG for Pods will work by default)
            # eks_cluster.cluster_security_group.add_ingress_rule(
            #    ec2.Peer.prefix_list(eks_vpc.vpc_cidr_block)
            #    ec2.Port.all_traffic()
            # )

            # Create an EFS Filesystem
            # NOTE In production you likely want to change the removal_policy to RETAIN to avoid accidental data loss
            efs_filesystem = efs.FileSystem(
                self,
                "EFSFilesystem",
                vpc=self.vpc,
                security_group=efs_security_group,
                removal_policy=RemovalPolicy.RETAIN,
            )
            cfn_efs_filesystem = cast(efs.CfnFileSystem, efs_filesystem.node.default_child)
            cfn_efs_filesystem.file_system_policy = iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        principals=[iam.AnyPrincipal()],
                        actions=[
                            "elasticfilesystem:ClientMount",
                            "elasticfilesystem:ClientWrite",
                            "elasticfilesystem:ClientRootAccess",
                        ],
                        resources=["*"],
                        conditions={"Bool": {"elasticfilesystem:AccessedViaMountTarget": "true"}},
                    ),
                    iam.PolicyStatement(
                        effect=iam.Effect.DENY,
                        principals=[iam.AnyPrincipal()],
                        actions=["*"],
                        resources=["*"],
                        conditions={"Bool": {"aws:SecureTransport": "false"}},
                    ),
                ]
            )

            # Set up the StorageClass pointing at the new CSI Driver
            # https://github.com/kubernetes-sigs/aws-efs-csi-driver/blob/master/examples/kubernetes/dynamic_provisioning/specs/storageclass.yaml
            efs_csi_storageclass = eks_cluster.add_manifest(
                "EFSCSIStorageClass",
                {
                    "kind": "StorageClass",
                    "apiVersion": "storage.k8s.io/v1",
                    "metadata": {"name": "efs"},
                    "provisioner": "efs.csi.aws.com",
                    "parameters": {
                        "provisioningMode": "efs-ap",
                        "fileSystemId": efs_filesystem.file_system_id,
                        "directoryPerms": "700",
                        "gidRangeStart": "1000",
                        "gidRangeEnd": "2000",
                        "basePath": "/dynamic_provisioning",
                    },
                },
            )
            efs_csi_storageclass.node.add_dependency(awsefscsi_chart)

        # AWS FSx CSI Driver
        if self.eks_addons_config.get("deploy_aws_fsx_csi", True):
            awsfsxcsidriver_service_account = eks_cluster.add_service_account(
                "awsfsxcsidriver", name="awsfsxcsidriver", namespace="kube-system"
            )

            awsfsxcsidriver_policy_statement_json_path = os.path.join(
                project_dir, "addons-iam-policies", "fsx-csi-iam.json"
            )
            with open(awsfsxcsidriver_policy_statement_json_path) as json_file:
                awsfsxcsidriver_policy_statement_json = json.load(json_file)

            # Attach the necessary permissions
            awsfsxcsidriver_policy = iam.Policy(
                self,
                "awsfsxcsidriverpolicy",
                document=iam.PolicyDocument.from_json(awsfsxcsidriver_policy_statement_json),
            )
            awsfsxcsidriver_service_account.role.attach_inline_policy(awsfsxcsidriver_policy)

            # Install the AWS FSx CSI Driver
            # https://github.com/kubernetes-sigs/aws-fsx-csi-driver/tree/release-0.9/charts/aws-fsx-csi-driver
            awsfsxcsi_chart = eks_cluster.add_helm_chart(
                "aws-fsx-csi-driver",
                chart="aws-fsx-csi-driver",
                version=get_version(str(self.eks_compute_config["eks_version"]), FSX_DRIVER_VERSION),
                release="awsfsxcsidriver",
                repository="https://kubernetes-sigs.github.io/aws-fsx-csi-driver",
                namespace="kube-system",
                values={
                    "controller": {"serviceAccount": {"create": False, "name": "awsfsxcsidriver"}},
                    "node": {"serviceAccount": {"create": False, "name": "awsfsxcsidriver"}},
                },
            )
            awsfsxcsi_chart.node.add_dependency(awsfsxcsidriver_service_account)

        # Cluster Autoscaler
        if self.eks_addons_config.get("deploy_cluster_autoscaler", True):
            clusterautoscaler_service_account = eks_cluster.add_service_account(
                "clusterautoscaler", name="clusterautoscaler", namespace="kube-system"
            )

            clusterautoscaler_policy_statement_json_path = os.path.join(
                project_dir, "addons-iam-policies", "cluster-autoscaler-iam.json"
            )
            with open(clusterautoscaler_policy_statement_json_path) as json_file:
                clusterautoscaler_policy_statement_json = json.load(json_file)

            # Attach the necessary permissions
            clusterautoscaler_policy = iam.Policy(
                self,
                "clusterautoscalerpolicy",
                document=iam.PolicyDocument.from_json(clusterautoscaler_policy_statement_json),
            )
            clusterautoscaler_service_account.role.attach_inline_policy(clusterautoscaler_policy)

            # Install the Cluster Autoscaler
            # For more info see https://github.com/kubernetes/autoscaler/tree/master/charts/cluster-autoscaler
            clusterautoscaler_chart = eks_cluster.add_helm_chart(
                "cluster-autoscaler",
                chart="cluster-autoscaler",
                version="9.11.0",
                release="clusterautoscaler",
                repository="https://kubernetes.github.io/autoscaler",
                namespace="kube-system",
                values={
                    "autoDiscovery": {"clusterName": eks_cluster.cluster_name},
                    "awsRegion": self.region,
                    "rbac": {"serviceAccount": {"create": False, "name": "clusterautoscaler"}},
                    "replicaCount": 2,
                    "extraArgs": {
                        "skip-nodes-with-system-pods": False,
                        "balance-similar-node-groups": True,
                    },
                },
            )
            clusterautoscaler_chart.node.add_dependency(clusterautoscaler_service_account)

        # Metrics Server (required for the Horizontal Pod Autoscaler (HPA))
        if self.eks_addons_config.get("deploy_metrics_server", True):
            # For more info see https://github.com/kubernetes-sigs/metrics-server/tree/master/charts/metrics-server
            # Changed from the Bitnami chart for Graviton/ARM64 support
            eks_cluster.add_helm_chart(
                "metrics-server",
                chart="metrics-server",
                version="3.7.0",
                release="metricsserver",
                repository="https://kubernetes-sigs.github.io/metrics-server/",
                namespace="kube-system",
                values={"resources": {"requests": {"cpu": "0.25", "memory": "0.5Gi"}}},
            )

        if self.eks_addons_config.get("deploy_external_dns", True):
            externaldns_service_account = eks_cluster.add_service_account(
                "external-dns", name="external-dns", namespace="kube-system"
            )

            # Create the PolicyStatements to attach to the role
            # See https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md#iam-policy
            # NOTE that this will give External DNS access to all Route53 zones
            # For production you'll likely want to replace 'Resource *' with specific resources
            externaldns_policy_statement_json_1 = {
                "Effect": "Allow",
                "Action": ["route53:ChangeResourceRecordSets"],
                "Resource": ["arn:aws:route53:::hostedzone/*"],
            }
            externaldns_policy_statement_json_2 = {
                "Effect": "Allow",
                "Action": ["route53:ListHostedZones", "route53:ListResourceRecordSets"],
                "Resource": ["*"],
            }

            # Attach the necessary permissions
            externaldns_service_account.add_to_principal_policy(
                iam.PolicyStatement.from_json(externaldns_policy_statement_json_1)
            )
            externaldns_service_account.add_to_principal_policy(
                iam.PolicyStatement.from_json(externaldns_policy_statement_json_2)
            )

            # Deploy External DNS from the bitnami Helm chart
            # For more info see https://github.com/kubernetes-sigs/external-dns/tree/master/charts/external-dns
            # Changed from the Bitnami chart for Graviton/ARM64 support
            externaldns_chart = eks_cluster.add_helm_chart(
                "external-dns",
                chart="external-dns",
                version="1.7.1",
                release="externaldns",
                repository="https://kubernetes-sigs.github.io/external-dns/",
                namespace="kube-system",
                values={
                    "serviceAccount": {"create": False, "name": "external-dns"},
                    "resources": {"requests": {"cpu": "0.25", "memory": "0.5Gi"}},
                },
            )
            externaldns_chart.node.add_dependency(externaldns_service_account)

        # Secrets Manager CSI Driver
        if self.eks_addons_config.get("deploy_secretsmanager_csi", True):
            # https://docs.aws.amazon.com/secretsmanager/latest/userguide/integrating_csi_driver.html

            # First we install the Secrets Store CSI Driver Helm Chart
            # https://github.com/kubernetes-sigs/secrets-store-csi-driver/tree/main/charts/secrets-store-csi-driver
            eks_cluster.add_helm_chart(
                "csi-secrets-store",
                chart="secrets-store-csi-driver",
                version="1.0.1",
                release="csi-secrets-store",
                repository="https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts",
                namespace="kube-system",
                # Since sometimes you want these secrets as environment variables enabling syncSecret
                # For more info see https://secrets-store-csi-driver.sigs.k8s.io/topics/sync-as-kubernetes-secret.html
                values={"syncSecret": {"enabled": True}},
            )

            # Install the AWS Provider
            # See https://github.com/aws/secrets-store-csi-driver-provider-aws for more info

            # Create the IRSA Mapping
            secrets_csi_sa = eks_cluster.add_service_account(
                "secrets-csi-sa", name="csi-secrets-store-provider-aws", namespace="kube-system"
            )

            # Associate the IAM Policy
            # NOTE: you really want to specify the secret ARN rather than * in the Resource
            # Consider namespacing these by cluster/environment name or some such as in this example:
            # "Resource": ["arn:aws:secretsmanager:Region:AccountId:secret:TestEnv/*"]
            secrets_csi_policy_statement_json_1 = {
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
                "Resource": ["*"],
            }
            secrets_csi_sa.add_to_principal_policy(iam.PolicyStatement.from_json(secrets_csi_policy_statement_json_1))

            # Deploy the manifests from secrets-store-csi-driver-provider-aws.yaml
            secrets_csi_provider_yaml_file = open("secrets-store-csi-driver-provider-aws.yaml", "r")
            secrets_csi_provider_yaml = list(yaml.load_all(secrets_csi_provider_yaml_file, Loader=yaml.FullLoader))
            secrets_csi_provider_yaml_file.close()
            loop_iteration = 0
            for value in secrets_csi_provider_yaml:
                # print(value)
                loop_iteration = loop_iteration + 1
                manifest_id = "SecretsCSIProviderManifest" + str(loop_iteration)
                manifest = eks_cluster.add_manifest(manifest_id, value)
                manifest.node.add_dependency(secrets_csi_sa)

        # Kubernetes External Secrets
        if self.eks_addons_config.get("deploy_external_secrets"):
            # Deploy the External Secrets Controller
            # Create the Service Account
            externalsecrets_service_account = eks_cluster.add_service_account(
                "kubernetes-external-secrets", name="kubernetes-external-secrets", namespace="kube-system"
            )

            # Define the policy in JSON
            externalsecrets_policy_statement_json_1 = {
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:GetResourcePolicy",
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret",
                    "secretsmanager:ListSecretVersionIds",
                ],
                "Resource": ["*"],
            }

            # Add the policies to the service account
            externalsecrets_service_account.add_to_principal_policy(
                iam.PolicyStatement.from_json(externalsecrets_policy_statement_json_1)
            )

            # Deploy the Helm Chart
            # https://github.com/external-secrets/kubernetes-external-secrets/tree/master/charts/kubernetes-external-secrets
            eks_cluster.add_helm_chart(
                "external-secrets",
                chart="kubernetes-external-secrets",
                version="8.5.1",
                repository="https://external-secrets.github.io/kubernetes-external-secrets/",
                namespace="kube-system",
                release="external-secrets",
                values={
                    "env": {"AWS_REGION": self.region},
                    "serviceAccount": {"name": "kubernetes-external-secrets", "create": False},
                    "securityContext": {"fsGroup": 65534},
                    "resources": {"requests": {"cpu": "0.25", "memory": "0.5Gi"}},
                },
            )

        # CloudWatch Container Insights - Metrics
        if self.eks_addons_config.get("deploy_cloudwatch_container_insights_metrics", True):
            # https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-setup-metrics.html

            # Create the Service Account
            cw_container_insights_sa = eks_cluster.add_service_account(
                "cloudwatch-agent", name="cloudwatch-agent", namespace="kube-system"
            )
            cw_container_insights_sa.role.add_managed_policy(
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchAgentServerPolicy")
            )

            # Set up the settings ConfigMap
            eks_cluster.add_manifest(
                "CWAgentConfigMap",
                {
                    "apiVersion": "v1",
                    "data": {
                        "cwagentconfig.json": '{\n  "logs": {\n    "metrics_collected": {\n      '
                        + '"kubernetes": {\n        "cluster_name": "'
                        + eks_cluster.cluster_name
                        + '",\n        "metrics_collection_interval": 60\n      }\n    },\n    '
                        + '"force_flush_interval": 5\n  }\n}\n'
                    },
                    "kind": "ConfigMap",
                    "metadata": {"name": "cwagentconfig", "namespace": "kube-system"},
                },
            )

            # Import cloudwatch-agent.yaml to a list of dictionaries and submit them as a manifest to EKS
            # Read the YAML file
            cw_agent_yaml_file = open("cloudwatch-agent.yaml", "r")
            cw_agent_yaml = list(yaml.load_all(cw_agent_yaml_file, Loader=yaml.FullLoader))
            cw_agent_yaml_file.close()
            loop_iteration = 0
            for value in cw_agent_yaml:
                # print(value)
                loop_iteration = loop_iteration + 1
                manifest_id = "CWAgent" + str(loop_iteration)
                eks_cluster.add_manifest(manifest_id, value)

        # CloudWatch Container Insights - Logs
        if self.eks_addons_config.get("deploy_cloudwatch_container_insights_logs"):
            # Create the Service Account
            fluentbit_cw_service_account = eks_cluster.add_service_account(
                "fluentbit-cw", name="fluentbit-cw", namespace="kube-system"
            )

            fluentbit_cw_policy_statement_json_1 = {
                "Effect": "Allow",
                "Action": [
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams",
                    "logs:DescribeLogGroups",
                    "logs:CreateLogStream",
                    "logs:CreateLogGroup",
                    "logs:PutRetentionPolicy",
                ],
                "Resource": ["*"],
            }

            # Add the policies to the service account
            fluentbit_cw_service_account.add_to_principal_policy(
                iam.PolicyStatement.from_json(fluentbit_cw_policy_statement_json_1)
            )

            # https://github.com/fluent/helm-charts/tree/main/charts/fluent-bit
            # https://docs.aws.amazon.com/eks/latest/userguide/fargate-logging.html
            fluentbit_chart_cw = eks_cluster.add_helm_chart(
                "fluentbit-cw",
                chart="fluent-bit",
                version="0.19.17",
                release="fluent-bit-cw",
                repository="https://fluent.github.io/helm-charts",
                namespace="kube-system",
                values={
                    "serviceAccount": {"create": False, "name": "fluentbit-cw"},
                    "config": {
                        "outputs": "[OUTPUT]\n    Name cloudwatch_logs\n    Match   *\n    region "
                        + self.region
                        + "\n    log_group_name fluent-bit-cloudwatch\n    log_stream_prefix from-fluent-bit-\n "
                        + "   auto_create_group true\n    log_retention_days "
                        + str(self.node.try_get_context("cloudwatch_container_insights_logs_retention_days"))
                        + "\n",
                        "filters.conf": "[FILTER]\n  Name  kubernetes\n  Match  kube.*\n  Merge_Log  On\n  "
                        + "Buffer_Size  0\n  Kube_Meta_Cache_TTL  300s",
                    },
                },
            )
            fluentbit_chart_cw.node.add_dependency(fluentbit_cw_service_account)

        # Amazon Managed Prometheus (AMP)
        if self.eks_addons_config.get("deploy_amp"):
            # https://aws.amazon.com/blogs/mt/getting-started-amazon-managed-service-for-prometheus/
            # Create AMP workspace
            amp_workspace = aps.CfnWorkspace(self, "AMPWorkspace")

            # Create IRSA mapping
            amp_sa = eks_cluster.add_service_account(
                "amp-sa", name="amp-iamproxy-service-account", namespace="kube-system"
            )

            # Associate the IAM Policy
            amp_policy_statement_json_1 = {
                "Effect": "Allow",
                "Action": [
                    "aps:RemoteWrite",
                    "aps:QueryMetrics",
                    "aps:GetSeries",
                    "aps:GetLabels",
                    "aps:GetMetricMetadata",
                ],
                "Resource": ["*"],
            }
            amp_sa.add_to_principal_policy(iam.PolicyStatement.from_json(amp_policy_statement_json_1))

            # Install Prometheus with a low 1 hour local retention to ship the metrics to the AMP
            # https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack
            # Changed this from just Prometheus to the Prometheus Operator for the additional functionality
            # Changed this to not use EBS PersistentVolumes so it'll work with Fargate Only Clusters
            # This should be acceptable as the metrics are immediatly streamed to the AMP
            amp_prometheus_chart = eks_cluster.add_helm_chart(
                "prometheus-chart",
                chart="kube-prometheus-stack",
                version="30.2.0",
                release="prometheus-for-amp",
                repository="https://prometheus-community.github.io/helm-charts",
                namespace="kube-system",
                values={
                    "prometheus": {
                        "serviceAccount": {
                            "create": False,
                            "name": "amp-iamproxy-service-account",
                            "annotations": {
                                "eks.amazonaws.com/role-arn": amp_sa.role.role_arn,
                            },
                        },
                        "prometheusSpec": {
                            "storageSpec": {"emptyDir": {"medium": "Memory"}},
                            "remoteWrite": [
                                {
                                    "queueConfig": {
                                        "maxSamplesPerSend": 1000,
                                        "maxShards": 200,
                                        "capacity": 2500,
                                    },
                                    "url": amp_workspace.attr_prometheus_endpoint + "api/v1/remote_write",
                                    "sigv4": {"region": self.region},
                                }
                            ],
                            "retention": "1h",
                            "resources": {"limits": {"cpu": 1, "memory": "1Gi"}},
                        },
                    },
                    "alertmanager": {"enabled": False},
                    "grafana": {"enabled": False},
                    "prometheusOperator": {
                        "admissionWebhooks": {"enabled": False},
                        "tls": {"enabled": False},
                        "resources": {"requests": {"cpu": "0.25", "memory": "0.5Gi"}},
                    },
                    "kubeControllerManager": {"enabled": False},
                    "kubeScheduler": {"enabled": False},
                    "kubeProxy": {"enabled": False},
                    "nodeExporter": {"enabled": False},
                },
            )
            amp_prometheus_chart.node.add_dependency(amp_sa)

        # Self-Managed Grafana for AMP
        if self.eks_addons_config.get("deploy_grafana_for_amp"):
            # Install a self-managed Grafana to visualise the AMP metrics
            # NOTE You likely want to use the AWS Managed Grafana (AMG) in production
            # We are using this as AMG requires SSO/SAML and is harder to include in the template
            # NOTE We are not enabling PersistentVolumes to allow this to run in Fargate making this immutable
            # Any changes to which dashboards to use should be deployed via the ConfigMaps in order to persist
            # https://github.com/grafana/helm-charts/tree/main/charts/grafana#sidecar-for-dashboards
            # For more information see https://github.com/grafana/helm-charts/tree/main/charts/grafana
            amp_grafana_chart = eks_cluster.add_helm_chart(
                "amp-grafana-chart",
                chart="grafana",
                version="6.21.1",
                release="grafana-for-amp",
                repository="https://grafana.github.io/helm-charts",
                namespace="kube-system",
                values={
                    "serviceAccount": {
                        "name": "amp-iamproxy-service-account",
                        "annotations": {"eks.amazonaws.com/role-arn": amp_sa.role.role_arn},
                        "create": False,
                    },
                    "grafana.ini": {"auth": {"sigv4_auth_enabled": True}},
                    "service": {
                        "type": "LoadBalancer",
                        "annotations": {
                            "service.beta.kubernetes.io/aws-load-balancer-type": "nlb-ip",
                            "service.beta.kubernetes.io/aws-load-balancer-internal": "true",
                        },
                    },
                    "datasources": {
                        "datasources.yaml": {
                            "apiVersion": 1,
                            "datasources": [
                                {
                                    "name": "Prometheus",
                                    "type": "prometheus",
                                    "access": "proxy",
                                    "url": amp_workspace.attr_prometheus_endpoint,
                                    "isDefault": True,
                                    "editable": True,
                                    "jsonData": {
                                        "httpMethod": "POST",
                                        "sigV4Auth": True,
                                        "sigV4AuthType": "default",
                                        "sigV4Region": self.region,
                                    },
                                }
                            ],
                        }
                    },
                    "sidecar": {"dashboards": {"enabled": True, "label": "grafana_dashboard"}},
                    "resources": {"requests": {"cpu": "0.25", "memory": "0.5Gi"}},
                },
            )
            amp_grafana_chart.node.add_dependency(amp_prometheus_chart)
            amp_grafana_chart.node.add_dependency(awslbcontroller_chart)

            # Dashboards for Grafana from the grafana-dashboards.yaml file
            grafana_dashboards_yaml_file = open("grafana-dashboards.yaml", "r")
            grafana_dashboards_yaml = list(yaml.load_all(grafana_dashboards_yaml_file, Loader=yaml.FullLoader))
            grafana_dashboards_yaml_file.close()
            loop_iteration = 0
            for value in grafana_dashboards_yaml:
                loop_iteration = loop_iteration + 1
                manifest_id = "GrafanaDashboard" + str(loop_iteration)
                eks_cluster.add_manifest(manifest_id, value)

        # Security Group for Pods
        # The EKS Cluster was still defaulting to 1.7.5 on 12/9/21 and SG for Pods requires 1.7.7
        # Upgrading that to the latest version 1.9.0 via the Helm Chart
        # If this process somehow breaks the CNI you can repair it manually by following the steps here:
        # https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html#updating-vpc-cni-add-on
        # TODO: Move this to the CNI Managed Add-on when that supports flipping the required ENABLE_POD_ENI setting

        # Adopting the existing aws-node resources to Helm
        patch_types = ["DaemonSet", "ClusterRole", "ClusterRoleBinding"]
        patches = []
        for kind in patch_types:
            patch = eks.KubernetesPatch(
                self,
                "CNI-Patch-" + kind,
                cluster=eks_cluster,
                resource_name=kind + "/aws-node",
                resource_namespace="kube-system",
                apply_patch={
                    "metadata": {
                        "annotations": {
                            "meta.helm.sh/release-name": "aws-vpc-cni",
                            "meta.helm.sh/release-namespace": "kube-system",
                        },
                        "labels": {"app.kubernetes.io/managed-by": "Helm"},
                    }
                },
                restore_patch={},
                patch_type=eks.PatchType.STRATEGIC,
            )
            # We don't want to clean this up on Delete - it is a one-time patch to let the Helm Chart own the resources
            patch_resource = patch.node.find_child("Resource")
            patch_resource.apply_removal_policy(RemovalPolicy.RETAIN)
            # Keep track of all the patches to set dependencies down below
            patches.append(patch)

        # Create the Service Account
        sg_pods_service_account = eks_cluster.add_service_account(
            "aws-node", name="aws-node-helm", namespace="kube-system"
        )

        # Give it the required policies
        sg_pods_service_account.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKS_CNI_Policy")
        )
        # sg_pods_service_account.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKSVPCResourceController"))
        eks_cluster.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKSVPCResourceController")
        )

        # https://github.com/aws/eks-charts/tree/master/stable/aws-vpc-cni
        # https://docs.aws.amazon.com/eks/latest/userguide/add-ons-images.html
        sg_pods_chart = eks_cluster.add_helm_chart(
            "aws-vpc-cni",
            chart="aws-vpc-cni",
            version="1.1.12",
            release="aws-vpc-cni",
            repository="https://aws.github.io/eks-charts",
            namespace="kube-system",
            values={
                "init": {
                    "image": {
                        "region": self.region,
                        "account": "602401143452",
                    },
                    "env": {"DISABLE_TCP_EARLY_DEMUX": True},
                },
                "image": {"region": self.region, "account": "602401143452"},
                "env": {"ENABLE_POD_ENI": True},
                "serviceAccount": {"create": False, "name": "aws-node-helm"},
                "crd": {"create": False},
                "originalMatchLabels": True,
            },
        )
        # This depends both on the service account and the patches to the existing CNI resources having been done first
        sg_pods_chart.node.add_dependency(sg_pods_service_account)
        for patch in patches:
            sg_pods_chart.node.add_dependency(patch)

        eks_cluster.add_manifest(
            "cluster-role",
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "ClusterRole",
                "metadata": {"name": "system-access"},
                "rules": [
                    {
                        "apiGroups": ["", "storage.k8s.io"],
                        "resources": ["persistentVolumes", "nodes", "storageClasses"],
                        "verbs": ["get", "watch", "list"],
                    }
                ],
            },
        )

        # Create a PodDisruptionBudget for ADDF Jobs
        eks_cluster.add_manifest(
            "addf-job-pdb",
            {
                "apiVersion": "policy/v1",
                "kind": "PodDisruptionBudget",
                "metadata": {
                    "name": "addf-job-pdb",
                },
                "spec": {
                    "minAvailable": 1,
                    "selector": {
                        "matchLabels": {"app": "addf-job"},
                    },
                },
            },
        )

        # Outputs
        self.eks_cluster = eks_cluster
        self.eks_cluster_masterrole = cluster_admin_role

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            apply_to_nested_stacks=True,
            suppressions=[
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Resource access restriced to ADDF resources",
                },
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Managed Policies are for service account roles only",
                },
                {
                    "id": "AwsSolutions-EKS1",
                    "reason": "No Customer data resides on the compute resources",
                },
            ],
        )
