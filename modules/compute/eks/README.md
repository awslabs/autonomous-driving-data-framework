# EKS

## Description

This module creates an EKS Cluster with the following features and addons available for use:

- Can create EKS Control plane and data plane in Private Subnets (having NATG in the route tables)
- Can create EKS Control plane in Private Subnets and data plane in Isolated Subnets (having Link local route in the route tables)
- Can launch application pods in secondary CIDR to save IP exhaustion in the primary CIDR
- Encrypts the root EBS volumes of managed node groups
- Can encrypt the EKS Control plane using Envelope encryption

### Plugins supported by category

Load balancing:

- ALB Ingress Controller
- Nginx Ingress Controller

Storage:

- EBS CSI Driver
- EFS CSI Driver
- FSX Lustre Driver

Secrets:

- Secrets Manager CSI Driver

Scaling:

- Horizontal Pod Autoscaler (HPA)
- CLuster Autoscaler (CA)

Monitoring/Logging/Alerting:

- Cloudwatch Container Insights (Metrics & logs)

Networking:

- Custom CIDR implementation
- Calico for network isolation/security

Security:

- Kyverno policies (policy as enforcement in k8s)

## Explaining the attributes

### Input Paramenters

#### Required

- `dataFiles`: Data files is a [seedfarmer feature](https://seed-farmer.readthedocs.io/en/latest/manifests.html#a-word-about-datafiles) which helps you to link a commonly available directory at the root of the repo. For EKS module, we declare the list of helm chart versions inside the supported `k8s-version.yaml` with the detailed metadata available inside the `default.yaml` for every supported plugin.
- `vpc-id`: The VPC-ID that the cluster will be created in
- `controlplane-subnet-ids`: The controlplane subnets that the EKS Cluster should be deployed in. These subnets should have internet connectivity enabled via NATG
- `dataplane-subnet-ids`: The dataplane subnets can be either private subnets (NATG enabled) or in isolated subnets(link local route only) depending on the compliance required to achieve
- `eks-compute` and `eks_nodegroup_config`: List of EKS Managed NodeGroup Configurations to use with the preferred EC2 instance types. The framework would automatically encrypt the root volume
- `eks-version`: The EKS Cluster version to lock the version to
- `eks-addons`: List of EKS addons to deploy on the EKS Cluster

#### Optional

- `custom-subnet-ids`: The custom subnets for assigning IP addresses to the pods. Usually used when there is a limited number of IP addresses available in the primary CIDR subnets. Refer to [custom networking](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network.html) for feature details 
- `eks_admin_role_name`: The Admin Role to be mapped to the `systems:masters` group of RBAC
- `eks_poweruser_role_name`: The PowerUser Role to be mapped to the `poweruser-group` group of RBAC
- `eks_readonly_role_name`: The ReadOnly Role to be mapped to the `readonly-group` group of RBAC
- `eks_node_spot`: If `eks_node_spot` is set to True, we deploy SPOT instances of the above `nodegroup_config` for you else we deploy `ON_DEMAND` instances.
- `eks_secrets_envelope_encryption`: If set to True, we enable KMS secret for [envelope encryption](https://aws.amazon.com/about-aws/whats-new/2020/03/amazon-eks-adds-envelope-encryption-for-secrets-with-aws-kms/) for Kubernetes secrets.
- `eks_api_endpoint_private`: If set to True, we deploy EKS cluster with API endpoint set to [private mode](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html).
- `deploy_aws_lb_controller`: Deploys the [ALB Ingress controller](https://docs.aws.amazon.com/eks/latest/userguide/alb-ingress.html). Default behavior is set to False
- `deploy_external_dns`: Deploys the External DNS to interact with [AWS Route53](https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md). Default behavior is set to False
- `deploy_aws_ebs_csi`: Deploys the [AWS EBS](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) Driver. Default behavior is set to False
- `deploy_aws_efs_csi`: Deploys the [AWS EFS](https://docs.aws.amazon.com/eks/latest/userguide/efs-csi.html). Default behavior is set to False
- `deploy_aws_fsx_csi`: Deploys the [AWS FSX](https://docs.aws.amazon.com/eks/latest/userguide/fsx-csi.html). Default behavior is set to False
- `deploy_cluster_autoscaler`: Deploys the [Cluster Autoscaler](https://docs.aws.amazon.com/eks/latest/userguide/autoscaling.html) to scale EKS Workers
- `deploy_metrics_server`: Deploys the [Metrics server](https://docs.aws.amazon.com/eks/latest/userguide/metrics-server.html) and HPA for scaling out/in pods. Default behavior is set to False
- `deploy_secretsmanager_csi`: Deploys [Secrets Manager CSI driver](https://docs.aws.amazon.com/secretsmanager/latest/userguide/integrating_csi_driver.html) to interact with Secrets mounted as files. Default behavior is set to False
- `deploy_cloudwatch_container_insights_metrics`: Deploys the [CloudWatch Agent](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-EKS-agent.html) to ingest containers metrics into AWS Cloudwatch. Default behavior is set to False
- `deploy_cloudwatch_container_insights_logs`: Deploys the [Fluent bit](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-setup-logs-FluentBit.html) plugin to ingest containers logs into AWS Cloudwatch. Default behavior is set to False
- `deploy_adot`: Deploys AWS Distro for OpenTelemetry (ADOT) which is a secure, production-ready, AWS supported distribution of the OpenTelemetry project.
- `deploy_amp`: Deploys AWS Managed Prometheus for centralized log monitoring - ELK Stack. Default behavior is set to False
- `deploy_grafana_for_amp`: Deploys Grafana boards for visualization of logs/metrics from Elasticsearch/Opensearch cluster. Default behavior is set to False
- `deploy_kured`: Deploys [kured reboot daemon](https://github.com/kubereboot/kured) that performs safe automatic node reboots when the need to do so is indicated by the package management system of the underlying OS. Default behavior is set to False
- `deploy_calico`: Deploys [Calico network engine](https://docs.aws.amazon.com/eks/latest/userguide/calico.html) and default-deny network policies. Default behavior is set to False.
- `deploy_nginx_controller`: Deploys [nginx ingress controller](https://aws.amazon.com/blogs/opensource/network-load-balancer-nginx-ingress-controller-eks/). You can provide `nginx_additional_annotations` which populates Optional list of nginx annotations. Default behavior is set to False
- `deploy_kyverno`: Deploys [Kyverno policy engine](https://aws.amazon.com/blogs/containers/managing-pod-security-on-amazon-eks-with-kyverno/) which is is a Policy-as-Code (PaC) solution that includes a policy engine designed for Kubernetes. You can provide the list of policies to be enabled using `kyverno_policies` attribute. Default behavior is set to False

### How to launch EKS Cluster in [Private Subnets](./docs/eks-private.md)

### How to launch EKS Cluster in [Isolated Subnets](./docs/eks-isolated.md)

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
  "EksClusterName": "idf-local-core-eks-cluster",
  "EksClusterAdminRoleArn": "arn:aws:iam::XXXXXXXX:role/idf-local-core-eks-stack-clusterCreationRoleXXXX",
  "EksClusterSecurityGroupId": "sg-XXXXXXXXXXXXXX",
  "EksOidcArn": "arn:aws:iam::XXXXXXXX:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/XXXXXXXX",
  "EksClusterOpenIdConnectIssuer": "oidc.eks.us-west-2.amazonaws.com/id/098FBE7B04A9C399E4A3534FF1C288C6",
  "CNIMetricsHelperRoleName": "idf-dataservice-core-eks-CNIMetricsHelperRole",
  "EksClusterMasterRoleArn" : "arn:aws:iam::XXXXXXXX:role/idf-local-core-eks-us-east-1-masterrole"
}

```
