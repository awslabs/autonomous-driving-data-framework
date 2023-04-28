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
import os
from typing import Any, Dict, cast

import cdk_nag
import yaml
from aws_cdk import Aspects, RemovalPolicy, Stack, Tags
from aws_cdk import aws_aps as aps
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_eks as eks
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk.lambda_layer_kubectl_v23 import KubectlV23Layer
from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

from helpers import (
    deep_merge,
    get_ami_version,
    get_az_from_subnet,
    get_chart_release,
    get_chart_repo,
    get_chart_values,
    get_chart_version,
)

project_dir = os.path.dirname(os.path.abspath(__file__))

# We are loading the data from docker replication module and use the following constants
# to get correct values from SSM
ALB_CONTROLLER = "alb_controller"
NGINX_CONTROLLER = "nginx_controller"
AWS_VPC_CNI = "aws_vpc_cni"
CALICO = "calico"
CLUSTER_AUTOSCALER = "cluster_autoscaler"
EBS_CSI_DRIVER = "ebs_csi_driver"
EFS_CSI_DRIVER = "efs_csi_driver"
EXTERNAL_DNS = "external_dns"
EXTERNAL_SECRETS = "external_secrets"
FLUENTBIT = "fluentbit"
FSX_DRIVER = "fsx_driver"
GRAFANA = "grafana"
KURED = "kured"
KYVERNO = "kyverno"
KYVERNO_POLICY_REPORTER = "kyverno_policy_reporter"
METRICS_SERVER = "metrics_server"
PROMETHEUS_STACK = "prometheus_stack"
SECRETS_MANAGER_CSI_DRIVER = "secrets_manager_csi_driver"


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

        # Disable pylint class has no member becase we load class attributes dynamically
        # pylint: disable=no-member
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

        self.private_subnets = []
        for idx, subnet_id in enumerate(self.private_subnet_ids):
            self.private_subnets.append(
                ec2.Subnet.from_subnet_id(scope=self, id=f"pri-subnet{idx}", subnet_id=subnet_id)
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
            "Action": [
                "iam:Create*",
                "iam:Put*",
                "iam:List*",
                "iam:Detach*",
                "iam:Attach*",
                "iam:DeleteRole",
            ],
            "Resource": [
                f"arn:aws:iam::{self.account}:role/AmazonEKSVPCCNIMetricsHelperRole",
                f"arn:aws:iam::{self.account}:policy/AmazonEKSVPCCNIMetricsHelperPolicy",
                f"arn:aws:iam::{self.account}:role/{self.cni_metrics_role_name}",
            ],
        }
        cluster_admin_role.add_to_principal_policy(iam.PolicyStatement.from_json(cluster_admin_policy_statement_json_1))
        cluster_admin_role.add_to_principal_policy(iam.PolicyStatement.from_json(cluster_admin_policy_statement_json_2))
        cluster_admin_role.add_to_principal_policy(iam.PolicyStatement.from_json(cluster_admin_policy_statement_json_3))

        if self.eks_compute_config.get("eks_secrets_envelope_encryption"):
            # KMS key for Kubernetes secrets envelope encryption
            secrets_key = kms.Key(self, "SecretsKey")

        # Creates an EKS Cluster
        eks_cluster = eks.Cluster(
            self,
            "cluster",
            vpc=self.vpc,
            vpc_subnets=[ec2.SubnetSelection(subnets=self.private_subnets)],
            cluster_name=f"addf-{self.deployment_name}-{self.module_name}-cluster",
            masters_role=cluster_admin_role,
            endpoint_access=eks.EndpointAccess.PRIVATE
            if self.eks_compute_config.get("eks_api_endpoint_private")
            else eks.EndpointAccess.PUBLIC,
            version=eks.KubernetesVersion.of(str(self.eks_version)),
            # Work around until CDK team makes kubectl upto date https://github.com/aws/aws-cdk/issues/23376
            kubectl_layer=KubectlV23Layer(self, "Kubectlv23Layer"),
            default_capacity=0,
            secrets_encryption_key=secrets_key
            if self.eks_compute_config.get("eks_secrets_envelope_encryption")
            else None,
            cluster_logging=[
                eks.ClusterLoggingTypes.API,
                eks.ClusterLoggingTypes.AUDIT,
                eks.ClusterLoggingTypes.AUTHENTICATOR,
                eks.ClusterLoggingTypes.CONTROLLER_MANAGER,
                eks.ClusterLoggingTypes.SCHEDULER,
            ],
        )

        # Whitelist traffic between Codebuild SG and EKS SG conditionally
        if self.eks_compute_config.get("eks_api_endpoint_private") and self.codebuild_sg_id:
            codebuild_sg = ec2.SecurityGroup.from_security_group_id(self, "eks-codebuild-sg", self.codebuild_sg_id)
            eks_cluster.kubectl_security_group.add_ingress_rule(
                codebuild_sg,
                ec2.Port.all_traffic(),
                description="Allowing traffic between private codebuild (codeseeder) and private API server",
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

        coredns_addon.node.add_dependency(eks_cluster)
        kube_proxy_addon.node.add_dependency(eks_cluster)

        # Adopting the existing aws-node resources to Helm to fix error `helm ownership errors`
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
        eks_cluster.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKSVPCResourceController")
        )

        custom_subnet_values = {}
        if self.custom_subnet_ids:
            custom_subnet_ids = get_az_from_subnet(self.custom_subnet_ids)
            custom_subnets_values = {}
            for subnet_id, subnet_availability_zone in custom_subnet_ids.items():
                custom_subnets_values[subnet_availability_zone] = {"id": subnet_id}

            custom_subnet_values = {
                "init": {
                    "env": {
                        "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": True,
                        "ENI_CONFIG_LABEL_DEF": "failure-domain.beta.kubernetes.io/zone",
                    },
                },
                "env": {
                    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": True,
                    "ENI_CONFIG_LABEL_DEF": "failure-domain.beta.kubernetes.io/zone",
                },
                "eniConfig": {
                    "create": True,
                    "subnets": custom_subnets_values,
                },
            }

        # Unfortunately vpc addon is always installed last, after the nodes are created and
        # we are unable to influence pod cidrs without recreating the nodes after the cluster creation.
        # To mitigate this and support out-of-the-box custom cidr for pods, we install
        # VPC CNI as a helm chart instead of vpc addon.
        # https://github.com/aws/eks-charts/tree/master/stable/aws-vpc-cni
        # https://docs.aws.amazon.com/eks/latest/userguide/add-ons-images.html
        vpc_cni_chart = eks_cluster.add_helm_chart(
            "aws-vpc-cni",
            chart=get_chart_release(str(self.eks_version), AWS_VPC_CNI),
            version=get_chart_version(str(self.eks_version), AWS_VPC_CNI),
            repository=get_chart_repo(str(self.eks_version), AWS_VPC_CNI),
            release="aws-vpc-cni",
            namespace="kube-system",
            values=deep_merge(
                {
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
                    "originalMatchLabels": True,
                },
                custom_subnet_values,
                get_chart_values(str(self.eks_version), AWS_VPC_CNI),
            ),
        )

        # This depends both on the service account and the patches to the existing CNI resources having been done first
        vpc_cni_chart.node.add_dependency(sg_pods_service_account)

        # Add a Managed Node Group
        if self.eks_compute_config.get("eks_nodegroup_config"):
            # Spot InstanceType
            if self.eks_compute_config.get("eks_node_spot"):
                node_capacity_type = eks.CapacityType.SPOT
            # OnDemand InstanceType
            else:
                node_capacity_type = eks.CapacityType.ON_DEMAND

            for ng in self.eks_compute_config.get("eks_nodegroup_config", [{}]):
                lt = ec2.CfnLaunchTemplate(
                    self,
                    f"ng-lt-{str(ng.get('eks_ng_name'))}",
                    launch_template_data=ec2.CfnLaunchTemplate.LaunchTemplateDataProperty(
                        instance_type=str(ng.get("eks_node_instance_type")),
                        block_device_mappings=[
                            ec2.CfnLaunchTemplate.BlockDeviceMappingProperty(
                                device_name="/dev/xvda",
                                ebs=ec2.CfnLaunchTemplate.EbsProperty(
                                    volume_type="gp3",
                                    volume_size=ng.get("eks_node_disk_size"),
                                    encrypted=True,
                                ),
                            )
                        ],
                    ),
                )

                nodegroup = eks_cluster.add_nodegroup_capacity(
                    f"cluster-default-{ng}",
                    capacity_type=node_capacity_type,
                    desired_size=ng.get("eks_node_quantity"),
                    min_size=ng.get("eks_node_min_quantity"),
                    max_size=ng.get("eks_node_max_quantity"),
                    # The default in CDK is to force upgrades through even if they violate - it is safer to not do that
                    force_update=False,
                    launch_template_spec=eks.LaunchTemplateSpec(id=lt.ref, version=lt.attr_latest_version_number),
                    labels=ng.get("eks_node_labels") if ng.get("eks_node_labels") else None,
                    release_version=get_ami_version(str(self.eks_version)),
                    subnets=ec2.SubnetSelection(subnets=self.private_subnets),
                )

                nodegroup.role.add_managed_policy(
                    iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
                )

                nodegroup.node.add_dependency(vpc_cni_chart)

        # AWS Load Balancer Controller
        if self.eks_addons_config.get("deploy_aws_lb_controller"):
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
                chart=get_chart_release(str(self.eks_version), ALB_CONTROLLER),
                version=get_chart_version(str(self.eks_version), ALB_CONTROLLER),
                repository=get_chart_repo(str(self.eks_version), ALB_CONTROLLER),
                release="awslbcontroller",
                namespace="kube-system",
                values=deep_merge(
                    {
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
                    get_chart_values(str(self.eks_version), ALB_CONTROLLER),
                ),
            )
            awslbcontroller_chart.node.add_dependency(awslbcontroller_service_account)

        # NGINX Ingress Controller
        if (
            "value" in self.eks_addons_config.get("deploy_nginx_controller")
            and self.eks_addons_config.get("deploy_nginx_controller")["value"]
        ):
            nginx_controller_service_account = eks_cluster.add_service_account(
                "nginx-controller",
                name="nginx-controller",
                namespace="kube-system",
            )

            # Create the PolicyStatements to attach to the role
            nginx_controller_policy_statement = iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "acm:DescribeCertificate",
                    "acm:ListCertificates",
                    "acm:GetCertificate",
                    "ec2:AuthorizeSecurityGroupIngress",
                    "ec2:CreateSecurityGroup",
                    "ec2:CreateTags",
                    "ec2:DeleteTags",
                    "ec2:DeleteSecurityGroup",
                    "ec2:DescribeAccountAttributes",
                    "ec2:DescribeAddresses",
                    "ec2:DescribeInstances",
                    "ec2:DescribeInstanceStatus",
                    "ec2:DescribeInternetGateways",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeTags",
                    "ec2:DescribeVpcs",
                    "ec2:ModifyInstanceAttribute",
                    "ec2:ModifyNetworkInterfaceAttribute",
                    "ec2:RevokeSecurityGroupIngress",
                ],
                resources=["*"],
            )

            # Attach the necessary permissions
            nginx_controller_policy = iam.Policy(
                self,
                "nginx-controller-policy",
                policy_name="nginx-controller-policy",
                statements=[nginx_controller_policy_statement],
            )
            nginx_controller_service_account.role.attach_inline_policy(nginx_controller_policy)

            custom_values = {}
            if "nginx_additional_annotations" in self.eks_addons_config.get("deploy_nginx_controller"):
                custom_values = {
                    "controller": {
                        "configAnnotations": self.eks_addons_config.get("deploy_nginx_controller")[
                            "nginx_additional_annotations"
                        ]
                    }
                }

            # Deploy the Nginx Ingress Controller
            # For more info check out https://github.com/kubernetes/ingress-nginx/tree/main/charts/ingress-nginx
            nginx_controller_chart = eks_cluster.add_helm_chart(
                "nginx-ingress",
                chart=get_chart_release(str(self.eks_version), NGINX_CONTROLLER),
                version=get_chart_version(str(self.eks_version), NGINX_CONTROLLER),
                repository=get_chart_repo(str(self.eks_version), NGINX_CONTROLLER),
                release="nginxcontroller",
                namespace="kube-system",
                values=deep_merge(
                    custom_values,
                    get_chart_values(str(self.eks_version), NGINX_CONTROLLER),
                ),
            )
            nginx_controller_chart.node.add_dependency(nginx_controller_service_account)

        # AWS EBS CSI Driver
        if self.eks_addons_config.get("deploy_aws_ebs_csi"):
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
                chart=get_chart_release(str(self.eks_version), EBS_CSI_DRIVER),
                version=get_chart_version(str(self.eks_version), EBS_CSI_DRIVER),
                repository=get_chart_repo(str(self.eks_version), EBS_CSI_DRIVER),
                release="awsebscsidriver",
                namespace="kube-system",
                values=deep_merge(
                    {
                        "controller": {
                            "region": self.region,
                            "serviceAccount": {
                                "create": False,
                                "name": "awsebscsidriver",
                            },
                        },
                        "node": {
                            "serviceAccount": {
                                "create": False,
                                "name": "awsebscsidriver",
                            }
                        },
                    },
                    get_chart_values(str(self.eks_version), EBS_CSI_DRIVER),
                ),
            )
            awsebscsi_chart.node.add_dependency(awsebscsidriver_service_account)

            # Set up the StorageClass pointing at the new CSI Driver
            # https://github.com/kubernetes-sigs/aws-ebs-csi-driver/blob/master/examples/kubernetes/dynamic-provisioning/specs/storageclass.yaml
            ebs_csi_storageclass = eks_cluster.add_manifest(
                "EBSCSIStorageClassGP2",
                {
                    "kind": "StorageClass",
                    "apiVersion": "storage.k8s.io/v1",
                    "metadata": {"name": "ebs-gp2"},
                    "parameters": {"type": "gp2", "encrypted": "true"},
                    "provisioner": "ebs.csi.aws.com",
                    "volumeBindingMode": "WaitForFirstConsumer",
                },
            )
            ebs_csi_storageclass.node.add_dependency(awsebscsi_chart)

            # Set up the StorageClass pointing at the new CSI Driver
            # https://github.com/kubernetes-sigs/aws-ebs-csi-driver/blob/master/examples/kubernetes/dynamic-provisioning/specs/storageclass.yaml
            ebs_csi_storageclass_gp3 = eks_cluster.add_manifest(
                "EBSCSIStorageClassGP3",
                {
                    "kind": "StorageClass",
                    "apiVersion": "storage.k8s.io/v1",
                    "metadata": {"name": "ebs-gp3"},
                    "parameters": {"type": "gp3", "encrypted": "true"},
                    "provisioner": "ebs.csi.aws.com",
                    "volumeBindingMode": "WaitForFirstConsumer",
                },
            )
            ebs_csi_storageclass_gp3.node.add_dependency(awsebscsi_chart)

        # AWS EFS CSI Driver
        if self.eks_addons_config.get("deploy_aws_efs_csi"):
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

            awsefscsi_chart = eks_cluster.add_helm_chart(
                "aws-efs-csi-driver",
                chart=get_chart_release(str(self.eks_version), EFS_CSI_DRIVER),
                version=get_chart_version(str(self.eks_version), EFS_CSI_DRIVER),
                repository=get_chart_repo(str(self.eks_version), EFS_CSI_DRIVER),
                release="awsefscsidriver",
                namespace="kube-system",
                values=deep_merge(
                    {
                        "controller": {
                            "serviceAccount": {
                                "create": False,
                                "name": "awsefscsidriver",
                            },
                            "deleteAccessPointRootDir": True,
                        },
                        "node": {
                            "serviceAccount": {
                                "create": False,
                                "name": "awsefscsidriver",
                            }
                        },
                    },
                    get_chart_values(str(self.eks_version), EFS_CSI_DRIVER),
                ),
            )

            awsefscsi_chart.node.add_dependency(awsefscsidriver_service_account)

        # AWS FSx CSI Driver does not work in isolated subnets at the time of developing the module
        if self.eks_addons_config.get("deploy_aws_fsx_csi"):
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
                chart=get_chart_release(str(self.eks_version), FSX_DRIVER),
                version=get_chart_version(str(self.eks_version), FSX_DRIVER),
                repository=get_chart_repo(str(self.eks_version), FSX_DRIVER),
                release="awsfsxcsidriver",
                namespace="kube-system",
                values=deep_merge(
                    {
                        "controller": {
                            "serviceAccount": {
                                "create": False,
                                "name": "awsfsxcsidriver",
                            }
                        },
                        "node": {
                            "serviceAccount": {
                                "create": False,
                                "name": "awsfsxcsidriver",
                            }
                        },
                    },
                    get_chart_values(str(self.eks_version), FSX_DRIVER),
                ),
            )
            awsfsxcsi_chart.node.add_dependency(awsfsxcsidriver_service_account)

        # Cluster Autoscaler
        if self.eks_addons_config.get("deploy_cluster_autoscaler"):
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
                chart=get_chart_release(str(self.eks_version), CLUSTER_AUTOSCALER),
                version=get_chart_version(str(self.eks_version), CLUSTER_AUTOSCALER),
                repository=get_chart_repo(str(self.eks_version), CLUSTER_AUTOSCALER),
                release="clusterautoscaler",
                namespace="kube-system",
                values=deep_merge(
                    {
                        "autoDiscovery": {"clusterName": eks_cluster.cluster_name},
                        "awsRegion": self.region,
                        "rbac": {
                            "serviceAccount": {
                                "create": False,
                                "name": "clusterautoscaler",
                            }
                        },
                        "replicaCount": 2,
                        "extraArgs": {
                            "skip-nodes-with-system-pods": False,
                            "balance-similar-node-groups": True,
                        },
                    },
                    get_chart_values(str(self.eks_version), CLUSTER_AUTOSCALER),
                ),
            )
            clusterautoscaler_chart.node.add_dependency(clusterautoscaler_service_account)

        # Metrics Server (required for the Horizontal Pod Autoscaler (HPA))
        if self.eks_addons_config.get("deploy_metrics_server"):
            # For more info see https://github.com/kubernetes-sigs/metrics-server/tree/master/charts/metrics-server
            # Changed from the Bitnami chart for Graviton/ARM64 support
            eks_cluster.add_helm_chart(
                "metrics-server",
                chart=get_chart_release(str(self.eks_version), METRICS_SERVER),
                version=get_chart_version(str(self.eks_version), METRICS_SERVER),
                repository=get_chart_repo(str(self.eks_version), METRICS_SERVER),
                release="metricsserver",
                namespace="kube-system",
                values=deep_merge(
                    {"resources": {"requests": {"cpu": "0.25", "memory": "0.5Gi"}}},
                    get_chart_values(str(self.eks_version), METRICS_SERVER),
                ),
            )

        if self.eks_addons_config.get("deploy_external_dns"):
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
                chart=get_chart_release(str(self.eks_version), EXTERNAL_DNS),
                version=get_chart_version(str(self.eks_version), EXTERNAL_DNS),
                repository=get_chart_repo(str(self.eks_version), EXTERNAL_DNS),
                release="externaldns",
                namespace="kube-system",
                values=deep_merge(
                    {
                        "serviceAccount": {"create": False, "name": "external-dns"},
                        "resources": {"requests": {"cpu": "0.25", "memory": "0.5Gi"}},
                    },
                    get_chart_values(str(self.eks_version), EXTERNAL_DNS),
                ),
            )
            externaldns_chart.node.add_dependency(externaldns_service_account)

        # Secrets Manager CSI Driver
        if self.eks_addons_config.get("deploy_secretsmanager_csi"):
            # https://docs.aws.amazon.com/secretsmanager/latest/userguide/integrating_csi_driver.html

            # First we install the Secrets Store CSI Driver Helm Chart
            # https://github.com/kubernetes-sigs/secrets-store-csi-driver/tree/main/charts/secrets-store-csi-driver
            eks_cluster.add_helm_chart(
                "csi-secrets-store",
                chart=get_chart_release(
                    str(self.eks_version),
                    SECRETS_MANAGER_CSI_DRIVER,
                ),
                version=get_chart_version(
                    str(self.eks_version),
                    SECRETS_MANAGER_CSI_DRIVER,
                ),
                repository=get_chart_repo(
                    str(self.eks_version),
                    SECRETS_MANAGER_CSI_DRIVER,
                ),
                release="csi-secrets-store",
                namespace="kube-system",
                # Since sometimes you want these secrets as environment variables enabling syncSecret
                # For more info see https://secrets-store-csi-driver.sigs.k8s.io/topics/sync-as-kubernetes-secret.html
                values=deep_merge(
                    {"syncSecret": {"enabled": True}},
                    get_chart_values(
                        str(self.eks_version),
                        SECRETS_MANAGER_CSI_DRIVER,
                    ),
                ),
            )
            # Install the AWS Provider
            # See https://github.com/aws/secrets-store-csi-driver-provider-aws for more info

            # Create the IRSA Mapping
            secrets_csi_sa = eks_cluster.add_service_account(
                "secrets-csi-sa",
                name="csi-secrets-store-provider-aws",
                namespace="kube-system",
            )

            # Associate the IAM Policy
            # NOTE: you really want to specify the secret ARN rather than * in the Resource
            # Consider namespacing these by cluster/environment name or some such as in this example:
            # "Resource": ["arn:aws:secretsmanager:Region:AccountId:secret:TestEnv/*"]
            secrets_csi_policy_statement_json_1 = {
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret",
                ],
                "Resource": ["*"],
            }
            secrets_csi_sa.add_to_principal_policy(iam.PolicyStatement.from_json(secrets_csi_policy_statement_json_1))

            # Deploy the manifests from secrets-store-csi-driver-provider-aws.yaml
            secrets_csi_provider_yaml_file = open("secrets-config/secrets-store-csi-driver-provider-aws.yaml", "r")
            secrets_csi_provider_yaml = list(yaml.load_all(secrets_csi_provider_yaml_file, Loader=yaml.FullLoader))
            secrets_csi_provider_yaml_file.close()
            loop_iteration = 0
            for value in secrets_csi_provider_yaml:
                loop_iteration = loop_iteration + 1
                manifest_id = "SecretsCSIProviderManifest" + str(loop_iteration)
                manifest = eks_cluster.add_manifest(manifest_id, value)
                manifest.node.add_dependency(secrets_csi_sa)

        # Kubernetes External Secrets
        if self.eks_addons_config.get("deploy_external_secrets"):
            # Deploy the External Secrets Controller
            # Create the Service Account
            externalsecrets_service_account = eks_cluster.add_service_account(
                "kubernetes-external-secrets",
                name="kubernetes-external-secrets",
                namespace="kube-system",
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
            # https://github.com/external-secrets/external-secrets/tree/main/deploy/charts/external-secrets
            eks_cluster.add_helm_chart(
                "external-secrets",
                chart=get_chart_release(str(self.eks_version), EXTERNAL_SECRETS),
                version=get_chart_version(str(self.eks_version), EXTERNAL_SECRETS),
                repository=get_chart_repo(str(self.eks_version), EXTERNAL_SECRETS),
                release="external-secrets",
                namespace="kube-system",
                values=deep_merge(
                    {
                        "env": {"AWS_REGION": self.region},
                        "serviceAccount": {
                            "name": "kubernetes-external-secrets",
                            "create": False,
                        },
                        "securityContext": {"fsGroup": 65534},
                        "resources": {"requests": {"cpu": "0.25", "memory": "0.5Gi"}},
                    },
                    get_chart_values(str(self.eks_version), EXTERNAL_SECRETS),
                ),
            )

        # CloudWatch Container Insights - Metrics
        if self.eks_addons_config.get("deploy_cloudwatch_container_insights_metrics"):
            # https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-setup-metrics.html

            # Create the Service Account
            cw_container_insights_sa = eks_cluster.add_service_account(
                "cloudwatch-agent", name="cloudwatch-agent", namespace="kube-system"
            )
            cw_container_insights_sa.role.add_managed_policy(
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchAgentServerPolicy")
            )

            # It opens cwagentconfig.json file in read mode ("r") and reads its content using the read() method. The content is stored in the cwagentconfig_content variable.
            with open(os.path.join(project_dir, "monitoring-config/cwagentconfig.json"), "r") as f:
                cwagentconfig_content = f.read()

            # Set up the settings ConfigMap
            eks_cluster.add_manifest(
                "CWAgentConfigMap",
                {
                    "apiVersion": "v1",
                    "kind": "ConfigMap",
                    "data": {
                        "cwagentconfig.json": cwagentconfig_content,
                    },
                    "metadata": {"name": "cwagentconfig", "namespace": "kube-system"},
                },
            )

            # Import cloudwatch-agent.yaml to a list of dictionaries and submit them as a manifest to EKS
            # Read the YAML file
            cw_agent_yaml_file = open(os.path.join(project_dir, "monitoring-config/cloudwatch-agent.yaml"), "r")
            cw_agent_yaml = list(yaml.load_all(cw_agent_yaml_file, Loader=yaml.FullLoader))
            cw_agent_yaml_file.close()
            loop_iteration = 0
            for value in cw_agent_yaml:
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
            fluentbit_chart_cw = eks_cluster.add_helm_chart(
                "fluentbit-cw",
                chart=get_chart_release(str(self.eks_version), FLUENTBIT),
                version=get_chart_version(str(self.eks_version), FLUENTBIT),
                repository=get_chart_repo(str(self.eks_version), FLUENTBIT),
                release="fluent-bit-cw",
                namespace="kube-system",
                values=deep_merge(
                    {
                        "serviceAccount": {"create": False, "name": "fluentbit-cw"},
                        "config": {
                            "outputs": "[OUTPUT]\n    Name cloudwatch_logs\n    Match   *\n    region "
                            + self.region
                            + "\n    log_group_name "
                            + eks_cluster.cluster_name
                            + "fluent-bit-cloudwatch\n    log_stream_prefix from-fluent-bit-\n "
                            + "   auto_create_group true\n    log_retention_days "
                            + str(self.node.try_get_context("cloudwatch_container_insights_logs_retention_days"))
                            + "\n",
                            "filters.conf": "[FILTER]\n  Name  kubernetes\n  Match  kube.*\n  Merge_Log  On\n  Buffer_Size  0\n  Kube_Meta_Cache_TTL  300s\n"
                            + "[FILTER]\n    Name modify\n    Match *\n    Rename log log_data\n    Rename stream stream_name\n"
                            + "[FILTER]\n    Name record_modifier\n    Match *\n    Record log_type startup\n"
                            + "[FILTER]\n    Name record_modifier\n    Match *\n    Record log_type shutdown\n"
                            + "[FILTER]\n    Name record_modifier\n    Match *\n    Record log_type error\n"
                            + "[FILTER]\n    Name record_modifier\n    Match *\n    Record log_type exception\n"
                            + "[FILTER]\n    Name record_modifier\n    Match *\n    Record log_type ingestion\n"
                            + "[FILTER]\n    Name record_modifier\n    Match *\n    Record log_type processing\n"
                            + "[FILTER]\n    Name record_modifier\n    Match *\n    Record log_type output\n"
                            + "[FILTER]\n    Name record_modifier\n    Match *\n    Record log_type performance\n"
                            + "\n",
                        },
                    },
                    get_chart_values(str(self.eks_version), FLUENTBIT),
                ),
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
                chart=get_chart_release(str(self.eks_version), PROMETHEUS_STACK),
                version=get_chart_version(str(self.eks_version), PROMETHEUS_STACK),
                repository=get_chart_repo(str(self.eks_version), PROMETHEUS_STACK),
                release="prometheus-for-amp",
                namespace="kube-system",
                values=deep_merge(
                    {
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
                    get_chart_values(str(self.eks_version), PROMETHEUS_STACK),
                ),
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
                chart=get_chart_release(str(self.eks_version), GRAFANA),
                version=get_chart_version(str(self.eks_version), GRAFANA),
                repository=get_chart_repo(str(self.eks_version), GRAFANA),
                release="grafana-for-amp",
                namespace="kube-system",
                values=deep_merge(
                    {
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
                        "sidecar": {
                            "dashboards": {
                                "enabled": True,
                                "label": "grafana_dashboard",
                            }
                        },
                        "resources": {"requests": {"cpu": "0.25", "memory": "0.5Gi"}},
                    },
                    get_chart_values(str(self.eks_version), GRAFANA),
                ),
            )
            amp_grafana_chart.node.add_dependency(amp_prometheus_chart)
            amp_grafana_chart.node.add_dependency(awslbcontroller_chart)

            # Dashboards for Grafana from the grafana-dashboards.yaml file
            grafana_dashboards_yaml_file = open("monitoring-config/grafana-dashboards.yaml", "r")
            grafana_dashboards_yaml = list(yaml.load_all(grafana_dashboards_yaml_file, Loader=yaml.FullLoader))
            grafana_dashboards_yaml_file.close()
            loop_iteration = 0
            for value in grafana_dashboards_yaml:
                loop_iteration = loop_iteration + 1
                manifest_id = "GrafanaDashboard" + str(loop_iteration)
                eks_cluster.add_manifest(manifest_id, value)

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

        # Defining the read only access role
        readonly_role_access_manifest = {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "Role",
            "metadata": {"name": "readonly-role"},
            "rules": [
                {
                    "apiGroups": [""],
                    "resources": ["*"],
                    "verbs": ["get", "list", "watch"],
                }
            ],
        }

        # Deploying the read only access role to the EKS cluster
        eks_cluster.add_manifest("readonly_role_access_manifest", readonly_role_access_manifest)

        # Defining the admin role access role
        admin_role_access_manifest = {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "ClusterRole",
            "metadata": {"name": "admin-role"},
            "rules": [
                {
                    "apiGroups": ["*"],
                    "resources": ["*"],
                    "verbs": [
                        "get",
                        "list",
                        "watch",
                        "create",
                        "delete",
                        "update",
                        "patch",
                    ],
                }
            ],
        }

        # Deploying the admin role access role to the EKS cluster
        eks_cluster.add_manifest("admin_role_access_manifest", admin_role_access_manifest)

        # Defining the poweruser role access role
        poweruser_role_access_manifest = {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "Role",
            "metadata": {"name": "poweruser-role"},
            "rules": [
                {
                    "apiGroups": ["", "apps", "extensions"],
                    "resources": ["*"],
                    "verbs": [
                        "get",
                        "list",
                        "watch",
                        "create",
                        "delete",
                        "update",
                        "patch",
                    ],
                }
            ],
        }

        # Deploying the poweruser role access role to the EKS cluster
        eks_cluster.add_manifest("poweruser_role_access_manifest", poweruser_role_access_manifest)

        # Define the RoleBinding manifest as a dictionary for readonly role
        readonly_role_binding_manifest = {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "RoleBinding",
            "metadata": {"name": "readonly-role-binding"},
            "subjects": [
                {
                    "kind": "Group",
                    "name": "readonly-group",
                    "apiGroup": "rbac.authorization.k8s.io",
                }
            ],
            "roleRef": {
                "kind": "Role",
                "name": "readonly-role",
                "apiGroup": "rbac.authorization.k8s.io",
            },
        }

        # Deploy the RoleBinding manifest to the EKS cluster for readonly role
        eks_cluster.add_manifest("readonly_role_binding_manifest", readonly_role_binding_manifest)

        # Define the RoleBinding manifest as a dictionary for admin role
        admin_role_binding_manifest = {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "ClusterRoleBinding",
            "metadata": {"name": "admin-role-binding"},
            "subjects": [
                {
                    "kind": "Group",
                    "name": "admin",
                    "apiGroup": "rbac.authorization.k8s.io",
                }
            ],
            "roleRef": {
                "kind": "ClusterRole",
                "name": "admin-role",
                "apiGroup": "rbac.authorization.k8s.io",
            },
        }

        # Deploy the RoleBinding manifest to the EKS cluster for admin role
        eks_cluster.add_manifest("admin_role_binding_manifest", admin_role_binding_manifest)

        # Define the RoleBinding manifest as a dictionary for poweruser role
        poweruser_role_binding_manifest = {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "RoleBinding",
            "metadata": {"name": "poweruser-role-binding"},
            "subjects": [
                {
                    "kind": "Group",
                    "name": "poweruser-group",
                    "apiGroup": "rbac.authorization.k8s.io",
                }
            ],
            "roleRef": {
                "kind": "Role",
                "name": "poweruser-role",
                "apiGroup": "rbac.authorization.k8s.io",
            },
        }

        # Deploy the RoleBinding manifest to the EKS cluster for admin role
        eks_cluster.add_manifest("poweruser_role_binding_manifest", poweruser_role_binding_manifest)

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

        if self.eks_addons_config.get("deploy_kured"):
            # https://kubereboot.github.io/charts/
            kured_chart = eks_cluster.add_helm_chart(
                "kured",
                chart=get_chart_release(str(self.eks_version), KURED),
                version=get_chart_version(str(self.eks_version), KURED),
                repository=get_chart_repo(str(self.eks_version), KURED),
                release="kured",
                namespace="kured",
                values=deep_merge(
                    {
                        "nodeSelector": {"kubernetes.io/os": "linux"},
                    },
                    get_chart_values(str(self.eks_version), KURED),
                ),
            )

        if self.eks_addons_config.get("deploy_calico"):
            calico_values = get_chart_values(str(self.eks_version), CALICO)
            if calico_values and "tigeraOperator" in calico_values and "registry" in calico_values["tigeraOperator"]:
                # https://docs.tigera.io/calico/3.25/reference/installation/api#operator.tigera.io/v1.InstallationSpec
                calico_values["installation"] = {}
                calico_values["installation"]["registry"] = calico_values["tigeraOperator"]["registry"]

            # https://docs.projectcalico.org/charts
            calico_chart = eks_cluster.add_helm_chart(
                "tigera-operator",
                chart=get_chart_release(str(self.eks_version), CALICO),
                version=get_chart_version(str(self.eks_version), CALICO),
                repository=get_chart_repo(str(self.eks_version), CALICO),
                values=deep_merge(
                    calico_values,
                ),
                release="calico",
                namespace="tigera-operator",
            )

            with open(os.path.join(project_dir, "network-policies/default-allow-kube-system.json"), "r") as f:
                default_allow_kube_system_policy_file = f.read()

            allow_kube_system_policy = eks_cluster.add_manifest(
                "default-allow-kube-system", json.loads(default_allow_kube_system_policy_file)
            )

            allow_kube_system_policy.node.add_dependency(calico_chart)

            with open(os.path.join(project_dir, "network-policies/default-allow-tigera-operator.json"), "r") as f:
                default_allow_tigera_operator_policy_file = f.read()

            allow_tigera_operator_policy = eks_cluster.add_manifest(
                "default-allow-tigera-operator", json.loads(default_allow_tigera_operator_policy_file)
            )

            allow_tigera_operator_policy.node.add_dependency(allow_kube_system_policy)

            with open(os.path.join(project_dir, "network-policies/default-deny.json"), "r") as f:
                default_deny_policy_file = f.read()

            default_deny_policy = eks_cluster.add_manifest("default-deny-policy", json.loads(default_deny_policy_file))

            default_deny_policy.node.add_dependency(allow_tigera_operator_policy)

        if (
            "value" in self.eks_addons_config.get("deploy_kyverno")
            and self.eks_addons_config.get("deploy_kyverno")["value"]
        ):
            # https://kyverno.github.io/kyverno/
            kyverno_chart = eks_cluster.add_helm_chart(
                "kyverno",
                chart=get_chart_release(str(self.eks_version), KYVERNO),
                version=get_chart_version(str(self.eks_version), KYVERNO),
                repository=get_chart_repo(str(self.eks_version), KYVERNO),
                values=deep_merge(
                    {
                        "resources": {
                            "limits": {"memory": "4Gi"},
                            "requests": {"cpu": "1", "memory": "1Gi"},
                        }
                    },
                    get_chart_values(str(self.eks_version), KYVERNO),
                ),
                release="kyverno",
                namespace="kyverno",
            )

            if self.eks_addons_config.get("deploy_calico"):

                with open(os.path.join(project_dir, "network-policies/default-allow-kyverno.json"), "r") as f:
                    default_allow_kyverno_policy_file = f.read()

                allow_kyverno_policy = eks_cluster.add_manifest(
                    "default-allow-kyverno", json.loads(default_allow_kyverno_policy_file)
                )

                allow_kyverno_policy.node.add_dependency(kyverno_chart)

            if "kyverno_policies" in self.eks_addons_config.get("deploy_kyverno"):
                all_policies = self.eks_addons_config.get("deploy_kyverno")["kyverno_policies"]
                for policy_type, policies in all_policies.items():
                    for policy in policies:
                        f = open(
                            os.path.join(project_dir, "kyverno-policies", policy_type, f"{policy}.yaml"),
                            "r",
                        ).read()
                        manifest_yaml = list(yaml.load_all(f, Loader=yaml.FullLoader))
                        previous_manifest = None
                        for value in manifest_yaml:
                            manifest_name = value["metadata"]["name"]
                            manifest = eks_cluster.add_manifest(manifest_name, value)
                            if previous_manifest == None:
                                manifest.node.add_dependency(kyverno_chart)
                            else:
                                manifest.node.add_dependency(previous_manifest)
                            previous_manifest = manifest

            kyverno_policy_reporter_chart = eks_cluster.add_helm_chart(
                "kyverno-policy-reporter",
                chart=get_chart_release(str(self.eks_version), KYVERNO_POLICY_REPORTER),
                version=get_chart_version(str(self.eks_version), KYVERNO_POLICY_REPORTER),
                repository=get_chart_repo(str(self.eks_version), KYVERNO_POLICY_REPORTER),
                release="policy-reporter",
                namespace="policy-reporter",
                values=deep_merge(
                    {
                        "kyvernoPlugin": {"enabled": True},
                        "ui": {
                            "enabled": True,
                            "plugins": {"kyverno": True},
                        },
                    },
                    get_chart_values(
                        str(self.eks_version),
                        KYVERNO_POLICY_REPORTER,
                    ),
                ),
            )

            kyverno_policy_reporter_chart.node.add_dependency(kyverno_chart)

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
                {
                    "id": "AwsSolutions-KMS5",
                    "reason": "The KMS Symmetric key does not have automatic key rotation enabled",
                },
            ],
        )
