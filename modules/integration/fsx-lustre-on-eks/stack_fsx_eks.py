from typing import Any, cast

import cdk_nag
from aws_cdk import Aspects, Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_eks as eks
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct


class FSXFileStorageOnEKS(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        deployment_name: str,
        module_name: str,
        fsx_dns_name: str,
        fsx_mount_name: str,
        fsx_file_system_id: str,
        fsx_security_group_id: str,
        eks_namespace: str,
        eks_cluster_name: str,
        eks_admin_role_arn: str,
        eks_oidc_arn: str,
        eks_cluster_security_group_id: str,
        **kwargs: Any,
    ) -> None:

        super().__init__(
            scope,
            id,
            description="This stack connects an existing FSX-Lustre to an existing EKS",
            **kwargs,
        )

        self.deployment_name = deployment_name
        self.module_name = module_name
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{self.deployment_name}")

        dep_mod = f"addf-{self.deployment_name}-{self.module_name}"
        dep_mod = dep_mod[:30]

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

        fsx_security_group = ec2.SecurityGroup.from_security_group_id(self, "FSXSecurityGroup", fsx_security_group_id)
        eks_security_group = ec2.SecurityGroup.from_security_group_id(
            self, "EKSSecurityGroup", eks_cluster_security_group_id
        )
        fsx_security_group.connections.allow_from(
            eks_security_group,
            ec2.Port.tcp(988),
            "allowtraffic from EKS nodes",
        )

        fsx_security_group.connections.allow_from(
            eks_security_group,
            ec2.Port.tcp(1021),
            "allowtraffic from EKS nodes",
        )

        fsx_security_group.connections.allow_from(
            eks_security_group,
            ec2.Port.tcp(1022),
            "allowtraffic from EKS nodes",
        )

        fsx_security_group.connections.allow_from(
            eks_security_group,
            ec2.Port.tcp(1023),
            "allowtraffic from EKS nodes",
        )

        self.storage_class_name = f"{module_name}-fsx-sc"
        self.pv_name = f"{module_name}-fsx-pv"
        self.pvc_name = f"{module_name}-fsx-pvc"

        eks_cluster.add_manifest(
            "FSXCSIStorageClass",
            {
                "apiVersion": "storage.k8s.io/v1",
                "kind": "StorageClass",
                "metadata": {"name": self.storage_class_name},
                "provisioner": "fsx.csi.aws.com",
                "reclaimPolicy": "Delete",
                "volumeBindingMode": "Immediate",
            },
        )

        eks_cluster.add_manifest(
            "FSXCSIPersistentVolume",
            {
                "apiVersion": "v1",
                "kind": "PersistentVolume",
                "metadata": {"name": self.pv_name},
                "spec": {
                    "storageClassName": self.storage_class_name,
                    "capacity": {"storage": "1200Gi"},
                    "volumeMode": "Filesystem",
                    "accessModes": ["ReadWriteMany"],
                    "mountOptions": ["flock"],
                    "persistentVolumeReclaimPolicy": "Recycle",
                    "csi": {
                        "driver": "fsx.csi.aws.com",
                        "volumeHandle": fsx_file_system_id,
                        "volumeAttributes": {"dnsname": fsx_dns_name, "mountname": fsx_mount_name},
                    },
                },
            },
        )

        eks_cluster.add_manifest(
            "FSXCSIPersistentVolumeClaim",
            {
                "apiVersion": "v1",
                "kind": "PersistentVolumeClaim",
                "metadata": {"name": self.pvc_name, "namespace": eks_namespace},
                "spec": {
                    "accessModes": ["ReadWriteMany"],
                    "resources": {"requests": {"storage": "1200Gi"}},
                    "storageClassName": self.storage_class_name,
                    "volumeMode": "Filesystem",
                    "volumeName": self.pv_name,
                },
            },
        )
        # Add a job that will change the permissions on FSx so that users w/o sudo can write to it
        eks_cluster.add_manifest(
            "SetPermissionsJob",
            {
                "apiVersion": "batch/v1",
                "kind": "Job",
                "metadata": {"name": "set-permissions-job", "namespace": eks_namespace},
                "spec": {
                    "ttlSecondsAfterFinished": 60,
                    "template": {
                        "metadata": {"annotations": {"sidecar.istio.io/inject": "false"}},
                        "spec": {
                            "restartPolicy": "Never",
                            "containers": [
                                {
                                    "name": "app",
                                    "image": "centos",
                                    "command": ["/bin/sh"],
                                    "args": ["-c", "chmod 2775 /data && chown root:users /data"],
                                    "volumeMounts": [{"name": "persistent-storage", "mountPath": "/data"}],
                                }
                            ],
                            "volumes": [
                                {"name": "persistent-storage", "persistentVolumeClaim": {"claimName": self.pvc_name}}
                            ],
                        },
                    },
                },
            },
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
            ],
        )
