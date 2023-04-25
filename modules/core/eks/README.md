# EKS


## Description

This module creates an EKS Cluster with the commonly preferred addons for use in ADDF


## Inputs/Outputs

### Input Paramenters

#### Required

- `vpc-id`: The VPC-ID that the cluster will be created in
- `private-subnet-ids`: The Private-Subnets that the EKS Cluster should be deployed in
- `eks_nodegroup_config`: List of EKS Managed NodeGroup Configurations to use with the preferred list of instance types
- `eks_version`: The EKS Cluster version to lock the version to

#### Optional

- `custom-subnet-ids`: The custom subnets for assigning IP addresses to the pods. Usually used when there is a limited number of IP addresses available for EKS.
- `eks_admin_role_name`: The Admin Role to be mapped to the `systems:masters` group of RBAC
- `eks_poweruser_role_name`: The PowerUser Role to be mapped to the `poweruser-group` group of RBAC
- `eks_readonly_role_name`: The ReadOnly Role to be mapped to the `readonly-group` group of RBAC
- `eks_node_spot`: If `eks_node_spot` is set to True, we deploy SPOT instances of the above `nodegroup_config` for you else we deploy `ON_DEMAND` instances.
- `eks_secrets_envelope_encryption`: If set to True, we enable KMS secret for envelope encryption for Kubernetes secrets.
- `eks_api_endpoint_private`: If set to True, we deploy EKS cluster with API endpoint set to private mode.
- `deploy_aws_lb_controller`: We deploy the ALB Ingress controller by default, unless you set it to False
- `deploy_external_dns`: We deploy the External DNS to interact with AWS Route53 by default, unless you set it to False
- `deploy_aws_ebs_csi`: We deploy the EBS CSI Driver AWS EBS by default, unless you set it to False
- `deploy_aws_efs_csi`: We deploy the EFS CSI Driver AWS EFS by default, unless you set it to False
- `deploy_aws_fsx_csi`: We deploy the FSX CSI Driver AWS FSX by default, unless you set it to False
- `deploy_cluster_autoscaler`: We deploy the Cluster Autoscaler to scale EKS Workers by default, unless you set it to False
- `deploy_metrics_server`: We deploy the Metrics Autoscaler to deploy HPA for scaling out/in pods, unless you set it to False
- `deploy_secretsmanager_csi`: We deploy Secrets Manager CSI to interact with Secrets mounted as files, unless you set it to False
- `deploy_cloudwatch_container_insights_metrics`: We deploy CloudWatch Container Insights plugin to ingest containers metrics into AWS Cloudwatch for you, unless you set it to False
- `deploy_cloudwatch_container_insights_logs`: If set to True, we deploy CloudWatch Container Insights plugin to ingest containers logs into AWS Cloudwatch for you. Default behavior is set to False
- `deploy_amp`: If set to True, we deploy AWS Managed Prometheus for you. Default behavior is set to False
- `deploy_grafana_for_amp`: If set to True, we deploy grafana boards. Default behavior is set to False
- `deploy_kured`: If set to True, we deploy kured reboot daemon. Default behavior is set to False
- `deploy_calico`: If set to True, we deploy calico network engine and default-deny network policies. Default behavior is set to False
- `deploy_nginx_controller`: If set to True, we deploy nginx ingress controller. Default behavior is set to False
- `nginx_additional_annotations`: Optional list of nginx annotations.
- `deploy_kyverno`: If set to True, we deploy Kyverno policy engine. Default behavior is set to False
- `kyverno_policies`: Optional list of validate and mutate kyverno policies.

### Sample declaration of EKS Compute Configuration

```yaml
- name: eks-compute
  value:
    eks_version: 1.25
    eks_admin_role_name: "Admin" 
    eks_nodegroup_config:
      - eks_ng_name: ng1
        eks_node_quantity: 2
        eks_node_max_quantity: 5
        eks_node_min_quantity: 1
        eks_node_disk_size: 20
        eks_node_instance_types: 
          - "m5.large"
      - eks_ng_name: ng2
        eks_node_quantity: 2
        eks_node_max_quantity: 5
        eks_node_min_quantity: 1
        eks_node_disk_size: 20
        eks_node_instance_types: 
          - "m5.xlarge"
        eks_node_labels:
          usage: visualization
    eks_node_spot: False
    eks_api_endpoint_private: False
```

> We have enabled [Security groups for pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html) by default as the best security practise and the feature is supported by most Nitro-based Amazon EC2 instance families. For finding the right instance type which supports the feature, refer to [limits.go](https://github.com/aws/amazon-vpc-resource-controller-k8s/blob/master/pkg/aws/vpc/limits.go)

### Sample declaration of EKS Addons Configuration

```yaml
- name: eks-addons
  value:
    deploy_aws_lb_controller: True # We deploy it unless set to False
    deploy_external_dns: True # We deploy it unless set to False
    deploy_aws_ebs_csi: True # We deploy it unless set to False
    deploy_aws_efs_csi: True # We deploy it unless set to False
    deploy_cluster_autoscaler: True # We deploy it unless set to False
    deploy_metrics_server: True # We deploy it unless set to False
    deploy_secretsmanager_csi: True # We deploy it unless set to False
    deploy_external_secrets: False
    deploy_cloudwatch_container_insights_metrics: True # We deploy it unless set to False
    deploy_cloudwatch_container_insights_logs: False
    cloudwatch_container_insights_logs_retention_days: 7
    deploy_amp: False 
    deploy_grafana_for_amp: False
    deploy_kured: False
    deploy_calico: False
    deploy_nginx_controller: False
    nginx_additional_annotations:
      nginx.ingress.kubernetes.io/whitelist-source-range: "100.64.0.0/10,10.0.0.0/8"
    deploy_kyverno: False
    kyverno_policies:
      validate:
        - block-ephemeral-containers
        - block-stale-images
        - block-updates-deletes
        - check-deprecated-apis
        - disallow-cri-sock-mount
        - disallow-custom-snippets
        - disallow-empty-ingress-host
        - disallow-helm-tiller
        - disallow-latest-tag
        - disallow-localhost-services
        - disallow-secrets-from-env-vars
        - ensure-probes-different
        - ingress-host-match-tls
        - limit-hostpath-vols
        - prevent-naked-pods
        - require-drop-cap-net-raw
        - require-emptydir-requests-limits
        - require-labels
        - require-pod-requests-limits
        - require-probes
        - restrict-annotations
        - restrict-automount-sa-token
        - restrict-binding-clusteradmin
        - restrict-clusterrole-nodesproxy
        - restrict-escalation-verbs-roles
        - restrict-ingress-classes
        - restrict-ingress-defaultbackend
        - restrict-node-selection
        - restrict-path
        - restrict-service-external-ips
        - restrict-wildcard-resources
        - restrict-wildcard-verbs
        - unique-ingress-host-and-path
```

#### IAM integration

EKS integrates with AWS Identity and Access Management (IAM) to control access to Kubernetes resources. IAM policies can be used to control access to Kubernetes API server and resources. EKS also supports role-based access control (RBAC), which allows you to define fine-grained access controls for users and groups. As of now we defined three roles, more roles can be added and refined as the requirements:
1. Admin role - allows full access to the namespaced and cluster-wide resources of EKS
2. Poweruser role - allows CRUD operations for namespaced resources of the EKS cluster
3. Read-only role - allows read operations for namespaced resources of the EKS cluster

#### Logging & Monitoring

- We have enabled [CloudWatch Container Insights](https://docs.aws.amazon.com/prescriptive-guidance/latest/implementing-logging-monitoring-cloudwatch/kubernetes-eks-metrics.html) by default as the standard practise for ingesting Cluster metrics to AWS CloudWatch

- For ingesting application logs, you could either enable `deploy_cloudwatch_container_insights_logs` flag in the above sample to write to AWS CloudWatch or deploy the module `eks-to-opensearch` under `modules/integration/` to write to AWS OpenSearch using fluent-bit logging driver.

### Module Metadata Outputs

- `EksClusterName`: The EKS Cluster Name
- `EksClusterAdminRoleArn`: The EKS Cluster's Admin Role Arn
- `EksClusterSecurityGroupId`: The EKS Cluster's SecurityGroup ID
- `EksOidcArn`: The EKS Cluster's OIDC Arn
- `EksClusterOpenIdConnectIssuer`: EKS Cluster's OPEN ID Issuer
- `CNIMetricsHelperRoleName`: Name of role created for CNIMetricHelper SA
- `EksClusterMasterRoleArn` - the masterrole used for cluster creation

#### Output Example

```json
{
  "EksClusterName": "addf-local-core-eks-cluster",
  "EksClusterAdminRoleArn": "arn:aws:iam::XXXXXXXX:role/addf-local-core-eks-stack-clusterCreationRoleXXXX",
  "EksClusterSecurityGroupId": "sg-XXXXXXXXXXXXXX",
  "EksOidcArn": "arn:aws:iam::XXXXXXXX:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/XXXXXXXX",
  "EksClusterOpenIdConnectIssuer": "oidc.eks.us-west-2.amazonaws.com/id/098FBE7B04A9C399E4A3534FF1C288C6",
  "CNIMetricsHelperRoleName": "addf-dataservice-core-eks-CNIMetricsHelperRole",
  "EksClusterMasterRoleArn" : "arn:aws:iam::XXXXXXXX:role/addf-local-core-eks-us-east-1-masterrole"
}

```
