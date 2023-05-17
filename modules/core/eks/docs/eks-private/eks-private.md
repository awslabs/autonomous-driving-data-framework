# EKS Cluster in Private Subnets

### Sample declaration of EKS module manifest

#### When deployed EKS Control plane and Data plane standalone in Private Subnets

```yaml
name: eks
path: modules/core/eks/
dataFiles:
  - filePath: data/eks_dockerimage-replication/versions/<<EKS_VERSION>>.yaml #replace the EKS_VERSION with the right EKS Cluster version
  - filePath: data/eks_dockerimage-replication/versions/default.yaml
parameters:
  - name: vpc-id
    valueFrom:
      moduleMetadata:
        group: optionals
        name: networking
        key: VpcId
  - name: controlplane-subnet-ids
    valueFrom:
      moduleMetadata:
        group: optionals
        name: networking
        key: PrivateSubnetIds
  - name: dataplane-subnet-ids
    valueFrom:
      moduleMetadata:
        group: optionals
        name: networking
        key: PrivateSubnetIds
  - name: eks-admin-role-name
    value: Admin
  - name: eks-poweruser-role-name
    value: PowerUser
  - name: eks-read-only-role-name
    value: ReadOnly
  - name: eks-version
    value: 1.25 # Replace the EKS_VERSION inline here or set an env var and load it from `.env` file using below format
    # valueFrom:
    #   envVariable: GLOBAL_EKS_VERSION
  - name: eks-compute
    value:
      eks_nodegroup_config:
        - eks_ng_name: ng1
          eks_node_quantity: 2
          eks_node_max_quantity: 5
          eks_node_min_quantity: 1
          eks_node_disk_size: 20
          eks_node_instance_type: "m5.large"
      eks_node_spot: False
      eks_api_endpoint_private: False # This makes the EKS Endpoint public
      eks_secrets_envelope_encryption: True 
  - name: eks-addons
    value:
      deploy_aws_lb_controller: True
      deploy_external_dns: True 
      deploy_aws_ebs_csi: True 
      deploy_aws_efs_csi: True 
      deploy_cluster_autoscaler: True 
      deploy_metrics_server: True 
      deploy_secretsmanager_csi: True 
      deploy_external_secrets: False
      deploy_cloudwatch_container_insights_metrics: True
      deploy_cloudwatch_container_insights_logs: True
      cloudwatch_container_insights_logs_retention_days: 7
      deploy_amp: False
      deploy_grafana_for_amp: False
      deploy_kured: False
      deploy_calico: False
      deploy_nginx_controller:
        value: False
        nginx_additional_annotations:
          nginx.ingress.kubernetes.io/whitelist-source-range: "100.64.0.0/10,10.0.0.0/8"
      deploy_kyverno:
        value: False
        kyverno_policies:
          validate:
            - block-ephemeral-containers
```

#### If you want to launch app pods in the extended VPC CIDR, follow the below manifest

```yaml
name: eks
path: modules/core/eks/
dataFiles:
  - filePath: data/eks_dockerimage-replication/versions/<<EKS_VERSION>>.yaml #replace the EKS_VERSION with the right EKS Cluster version
  - filePath: data/eks_dockerimage-replication/versions/default.yaml
parameters:
  - name: vpc-id
    valueFrom:
      moduleMetadata:
        group: optionals
        name: networking
        key: VpcId
  - name: controlplane-subnet-ids
    valueFrom:
      moduleMetadata:
        group: optionals
        name: networking
        key: PrivateSubnetIds
  - name: dataplane-subnet-ids
    valueFrom:
      moduleMetadata:
        group: optionals
        name: networking
        key: PrivateSubnetIds
  - name: custom-subnet-ids # Make sure to extend VPC CIDR before you launch EKS cluster and substitute the extended subnet IDS below
    value: ["subnet-XXXXXXXXX", "subnet-XXXXXXXXX"]
  - name: eks-admin-role-name
    value: Admin
  - name: eks-poweruser-role-name
    value: PowerUser
  - name: eks-read-only-role-name
    value: ReadOnly
  - name: eks-version
    value: 1.25 # Replace the EKS_VERSION inline here or set an env var and load it from `.env` file using below format
    # valueFrom:
    #   envVariable: GLOBAL_EKS_VERSION
  - name: eks-compute
    value:
      eks_nodegroup_config:
        - eks_ng_name: ng1
          eks_node_quantity: 2
          eks_node_max_quantity: 5
          eks_node_min_quantity: 1
          eks_node_disk_size: 20
          eks_node_instance_type: "m5.large"
      eks_node_spot: False
      eks_api_endpoint_private: False # This makes the EKS Endpoint public
      eks_secrets_envelope_encryption: True 
  - name: eks-addons
    value:
      deploy_aws_lb_controller: True
      deploy_external_dns: True 
      deploy_aws_ebs_csi: True 
      deploy_aws_efs_csi: True 
      deploy_cluster_autoscaler: True 
      deploy_metrics_server: True 
      deploy_secretsmanager_csi: True 
      deploy_external_secrets: False
      deploy_cloudwatch_container_insights_metrics: True
      deploy_cloudwatch_container_insights_logs: True
      cloudwatch_container_insights_logs_retention_days: 7
      deploy_amp: False
      deploy_grafana_for_amp: False
      deploy_kured: False
      deploy_calico: False
      deploy_nginx_controller:
        value: False
        nginx_additional_annotations:
          nginx.ingress.kubernetes.io/whitelist-source-range: "100.64.0.0/10,10.0.0.0/8"
      deploy_kyverno:
        value: False
        kyverno_policies:
          validate:
            - block-ephemeral-containers
```
