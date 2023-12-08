# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import sys

import pytest


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project"
    os.environ["SEEDFARMER_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["SEEDFARMER_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
    os.environ["SEEDFARMER_PARAMETER_RETENTION_TYPE"] = "DESTROY"
    os.environ["SEEDFARMER_PARAMETER_VPC_ID"] = "vpc-12345"
    os.environ["SEEDFARMER_PARAMETER_DATAPLANE_SUBNET_IDS"] = '["subnet-12345", "subnet-54321"]'
    os.environ["SEEDFARMER_PARAMETER_CONTROLPLANE_SUBNET_IDS"] = '["subnet-12345", "subnet-54321"]'
    os.environ["SEEDFARMER_PARAMETER_EKS_VERSION"] = "1.25"
    os.environ[
        "SEEDFARMER_PARAMETER_EKS_COMPUTE"
    ] = '{"eks_nodegroup_config": [{"eks_ng_name": "ng1", "eks_node_quantity": 2, "eks_node_max_quantity": 5, "eks_node_min_quantity": 1, "eks_node_disk_size": 20, "eks_node_instance_type": "m5.large"}, {"eks_ng_name": "ng2", "eks_node_quantity": 2, "eks_node_max_quantity": 5, "eks_node_min_quantity": 1, "eks_node_disk_size": 20, "eks_node_instance_type": "m5.xlarge"}], "eks_node_spot": "False", "eks_api_endpoint_private": "False", "eks_secrets_envelope_encryption": "True"}'
    os.environ[
        "SEEDFARMER_PARAMETER_EKS_ADDONS"
    ] = '{"deploy_aws_lb_controller": "True", "deploy_external_dns": "True", "deploy_aws_ebs_csi": "True", "deploy_aws_efs_csi": "True", "deploy_cluster_autoscaler": "True", "deploy_metrics_server": "True", "deploy_secretsmanager_csi": "True", "deploy_external_secrets": "False", "deploy_cloudwatch_container_insights_metrics": "True", "deploy_cloudwatch_container_insights_logs": "True", "cloudwatch_container_insights_logs_retention_days": 7, "deploy_amp": "True", "deploy_adot": "True", "deploy_grafana_for_amp": "True", "deploy_kured": "True", "deploy_calico": "False", "deploy_nginx_controller": {"value": "False", "nginx_additional_annotations": {"nginx.ingress.kubernetes.io/whitelist-source-range": "100.64.0.0/10,10.0.0.0/8"}}, "deploy_kyverno": {"value": "False", "kyverno_policies": {"validate": ["block-ephemeral-containers", "block-stale-images", "block-updates-deletes", "check-deprecated-apis", "disallow-cri-sock-mount", "disallow-custom-snippets", "disallow-empty-ingress-host", "disallow-helm-tiller", "disallow-latest-tag", "disallow-localhost-services", "disallow-secrets-from-env-vars", "ensure-probes-different", "ingress-host-match-tls", "limit-hostpath-vols", "prevent-naked-pods", "require-drop-cap-net-raw", "require-emptydir-requests-limits", "require-labels", "require-pod-requests-limits", "require-probes", "restrict-annotations", "restrict-automount-sa-token", "restrict-binding-clusteradmin", "restrict-clusterrole-nodesproxy", "restrict-escalation-verbs-roles", "restrict-ingress-classes", "restrict-ingress-defaultbackend", "restrict-node-selection", "restrict-path", "restrict-service-external-ips", "restrict-wildcard-resources", "restrict-wildcard-verbs", "unique-ingress-host-and-path"]}}}'  # type: ignore

    # Unload the app import so that subsequent tests don't reuse
    if "app" in sys.modules:
        del sys.modules["app"]


def test_app(stack_defaults):
    import app  # noqa: F401


def test_project_deployment_name_length(stack_defaults):
    os.environ["SEEDFARMER_PROJECT_NAME"] = "test-project-incredibly"

    with pytest.raises(Exception) as e:
        import app  # noqa: F401
    assert "module cannot support a project+deployment name character length greater than" in str(e)


def test_vpc_id(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_VPC_ID"]

    with pytest.raises(Exception):
        import app  # noqa: F401

        assert os.environ["SEEDFARMER_PARAMETER_VPC_ID"] == "vpc-12345"


def test_dataplame_subnet_ids(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_DATAPLANE_SUBNET_IDS"]

    with pytest.raises(Exception):
        import app  # noqa: F401

        assert os.environ["SEEDFARMER_PARAMETER_DATAPLANE_SUBNET_IDS"] == ["subnet-12345", "subnet-54321"]


def test_controlplane_subnet_ids(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_CONTROLPLANE_SUBNET_IDS"]

    with pytest.raises(Exception):
        import app  # noqa: F401

        assert os.environ["SEEDFARMER_PARAMETER_CONTROLPLANE_SUBNET_IDS"] == ["subnet-12345", "subnet-54321"]


def test_eks_compute(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_EKS_COMPUTE"]

    with pytest.raises(Exception):
        import app  # noqa: F401

        assert os.environ["SEEDFARMER_PARAMETER_EKS_COMPUTE"] == {
            "eks_nodegroup_config": [
                {
                    "eks_ng_name": "ng1",
                    "eks_node_quantity": 2,
                    "eks_node_max_quantity": 5,
                    "eks_node_min_quantity": 1,
                    "eks_node_disk_size": 20,
                    "eks_node_instance_type": "m5.large",
                }
            ],
            "eks_node_spot": "False",
            "eks_api_endpoint_private": "False",
            "eks_secrets_envelope_encryption": "True",
        }


def test_eks_addons(stack_defaults):
    del os.environ["SEEDFARMER_PARAMETER_EKS_ADDONS"]

    with pytest.raises(Exception):
        import app  # noqa: F401

        assert os.environ["SEEDFARMER_PARAMETER_EKS_ADDONS"] == {
            "deploy_aws_lb_controller": "True",
            "deploy_external_dns": "True",
            "deploy_aws_ebs_csi": "True",
            "deploy_aws_efs_csi": "True",
            "deploy_cluster_autoscaler": "True",
            "deploy_metrics_server": "True",
            "deploy_secretsmanager_csi": "True",
            "deploy_external_secrets": "False",
            "deploy_cloudwatch_container_insights_metrics": "True",
            "deploy_cloudwatch_container_insights_logs": "True",
            "cloudwatch_container_insights_logs_retention_days": 7,
            "deploy_amp": "True",
            "deploy_adot": "True",
            "deploy_grafana_for_amp": "True",
            "deploy_kured": "True",
            "deploy_calico": "False",
            "deploy_nginx_controller": {
                "value": "False",
                "nginx_additional_annotations": {
                    "nginx.ingress.kubernetes.io/whitelist-source-range": "100.64.0.0/10,10.0.0.0/8"
                },
            },
            "deploy_kyverno": {"value": "False", "kyverno_policies": {"validate": ["block-ephemeral-containers"]}},
        }
