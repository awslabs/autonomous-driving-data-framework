# EKS Cluster in Isolated Subnets

## Sample declaration of EKS module manifest

### If your environment doesnt have internet access via IGW/NATG, then the recommended approach is below

- Make sure to launch EKS Control plane in private subnets which gives the lambda functions launched by CDK an ability to talk to helm registries
- Make sure to launch EKS Data plane in isolated subnets which has no internet connectivity
- Make sure to validate your isolated subnets has relevant Interface endpoints to talk to respective AWS APIs privately

### Below is how `deployment.yaml` should look like

```yaml
name: test-deploy
toolchainRegion: eu-west-2
groups:
  - name: replication
    path: manifests/demo-isolated/replicator-modules.yaml
  - name: core
    path: manifests/demo-isolated/core-modules.yaml
targetAccountMappings:
  - alias: primary
    accountId: 1234567890
    default: true
    # parametersGlobal:
    regionMappings:
      - region: eu-west-2
        default: true
        parametersRegional:
          dockerCredentialsSecret: aws-idf-docker-credentials
          # replace the below networking details with customer specific values
          vpcId: vpc-XXXXXXXX
          publicSubnetIds:
            - subnet-XXXXXXXX
            - subnet-XXXXXXXX
          privateSubnetIds:
            - subnet-XXXXXXXX
            - subnet-XXXXXXXX
          isolatedSubnetIds:
            - subnet-XXXXXXXX
            - subnet-XXXXXXXX
          securityGroupIds:
            - sg-XXXXXXXX
        # these networking values will be used for seedfarmer's codebuild environment
        network: 
          vpcId:
            valueFrom:
              parameterValue: vpcId
            # Alternatively you can grab the networking values from SSM parameter store
            # valueFrom:
            #   parameterStore: /idf/vpc-id
          privateSubnetIds:
            valueFrom:
              parameterValue: privateSubnetIds
            # Alternatively you can grab the networking values from SSM parameter store
            # valueFrom:
            #   parameterStore: /idf/private-ids
          securityGroupIds:
            valueFrom:
              parameterValue: securityGroupIds
            # Alternatively you can grab the codebuild security group from SSM parameter store
            # valueFrom:
            #   parameterStore: /idf/sg-ids
```

```observation
- The above will launch codebuild trigerred via seedfarmer inside the above configured VPC which would have ability to talk to EKS private API.
```

### Deploy `docker-image` replications module which would replicate the docker images embedded inside the specified version of helm charts sourced from `data` folder. Sample declaration of `docker-image` replications module is below

```yaml
name: replication
path: modules/replication/dockerimage-replication/
dataFiles:
  - filePath: data/eks_dockerimage-replication/versions/<<EKS_VERSION>>.yaml #replace the EKS_VERSION with the right EKS Cluster version
  - filePath: data/eks_dockerimage-replication/versions/default.yaml
parameters:
  - name: eks-version
    value: 1.25
    # valueFrom:
    #   envVariable: GLOBAL_EKS_VERSION
```

```observation
- The above would replicate the docker images from public registries into an AWS account private ECR.
- The replicated docker images inventory json is available under an s3 bucket path, which should be consumed in EKS module
```

### Next, deploy `EKS` module using the below sample manifest

```yaml
name: eks
path: modules/core/eks/
dataFiles:
  - filePath: data/eks_dockerimage-replication/versions/<<EKS_VERSION>>.yaml #replace the EKS_VERSION with the right EKS Cluster version
  - filePath: data/eks_dockerimage-replication/versions/default.yaml
parameters:
  - name: replicated-ecr-images-metadata-s3-path # this parameter will load replicated images inventory from s3 bucket
    valueFrom:
      moduleMetadata:
        group: replication
        name: replication
        key: s3_full_path
  - name: vpc-id
    value: 
    valueFrom:
      parameterValue: vpcId
  - name: controlplane-subnet-ids # the below would grab the subnet ids declared in deployment.yaml or you can declare inline
    valueFrom:
      parameterValue: privateSubnetIds
  - name: dataplane-subnet-ids # the below would grab the subnet ids declared in deployment.yaml
    valueFrom:
      parameterValue: isolatedSubnetIds
  - name: codebuild-sg-id # the below would establish network connectivity between EKS API server and codebuild
    valueFrom:
      parameterValue: securityGroupIds
  - name: eks-admin-role-name
    value: Admin
  - name: eks-poweruser-role-name
    value: PowerUser
  - name: eks-read-only-role-name
    value: ReadOnly
  - name: eks-version
    # value: 1.25
    valueFrom:
      envVariable: GLOBAL_EKS_VERSION
  - name: eks-compute
    value:
      eks_nodegroup_config:
        - eks_ng_name: ng1
          eks_node_quantity: 2
          eks_node_max_quantity: 5
          eks_node_min_quantity: 1
          eks_node_disk_size: 20
          eks_node_instance_type: "m5.large"
        - eks_ng_name: ng2
          eks_node_quantity: 2
          eks_node_max_quantity: 5
          eks_node_min_quantity: 1
          eks_node_disk_size: 20
          eks_node_instance_type: "m5.xlarge"
      eks_node_spot: False
      eks_api_endpoint_private: True
      eks_secrets_envelope_encryption: True
  - name: eks-addons
    value:
      deploy_aws_lb_controller: True # We deploy it unless set to False
      deploy_external_dns: True # We deploy it unless set to False
      deploy_aws_ebs_csi: True # We deploy it unless set to False
      deploy_aws_efs_csi: True # We deploy it unless set to False
      deploy_cluster_autoscaler: True # We deploy it unless set to False
      deploy_metrics_server: True # We deploy it unless set to False
      deploy_secretsmanager_csi: False # We deploy it unless set to False
      deploy_external_secrets: False
      deploy_cloudwatch_container_insights_metrics: True # We deploy it unless set to False
      deploy_cloudwatch_container_insights_logs: True
      cloudwatch_container_insights_logs_retention_days: 7
      deploy_amp: True
      deploy_grafana_for_amp: True
      deploy_kured: True
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
  - name: replicated-ecr-images-metadata-s3-path # this parameter will load replicated images inventory from s3 bucket
    valueFrom:
      moduleMetadata:
        group: replication
        name: replication
        key: s3_full_path
  # the below would grab the vpc id declared in deployment.yaml
  - name: vpc-id
    valueFrom:
      parameterValue: vpcId
#  the below would grab the vpc id declared inline
#   - name: vpc-id
#     value: "vpc-XXXXX"
  # the below would grab the subnet ids declared in deployment.yaml
  - name: controlplane-subnet-ids  
    valueFrom:
      parameterValue: privateSubnetIds
#  the below would grab the subnet ids declared inline
#   - name: controlplane-subnet-ids  
#     value: ["subnet-XXXXXXXXX", "subnet-XXXXXXXXX"]
  - name: dataplane-subnet-ids # the below would grab the subnet ids declared in deployment.yaml
    valueFrom:
      parameterValue: isolatedSubnetIds
  - name: custom-subnet-ids # Make sure to extend VPC CIDR before you launch EKS cluster and substitute the extended subnet IDS below
    valueFrom:
      parameterValue: customSubnetIds
  - name: codebuild-sg-id # the below would establish network connectivity between EKS API server and codebuild
    valueFrom:
      parameterValue: securityGroupIds
  - name: eks-admin-role-name
    value: Admin
  - name: eks-poweruser-role-name
    value: PowerUser
  - name: eks-read-only-role-name
    value: ReadOnly
  - name: eks-version
    # value: 1.25
    valueFrom:
      envVariable: GLOBAL_EKS_VERSION
  - name: eks-compute
    value:
      eks_nodegroup_config:
        - eks_ng_name: ng1
          eks_node_quantity: 2
          eks_node_max_quantity: 5
          eks_node_min_quantity: 1
          eks_node_disk_size: 20
          eks_node_instance_type: "m5.large"
        - eks_ng_name: ng2
          eks_node_quantity: 2
          eks_node_max_quantity: 5
          eks_node_min_quantity: 1
          eks_node_disk_size: 20
          eks_node_instance_type: "m5.xlarge"
      eks_node_spot: False
      eks_api_endpoint_private: True
      eks_secrets_envelope_encryption: True
  - name: eks-addons
    value:
      deploy_aws_lb_controller: True # We deploy it unless set to False
      deploy_external_dns: True # We deploy it unless set to False
      deploy_aws_ebs_csi: True # We deploy it unless set to False
      deploy_aws_efs_csi: True # We deploy it unless set to False
      deploy_cluster_autoscaler: True # We deploy it unless set to False
      deploy_metrics_server: True # We deploy it unless set to False
      deploy_secretsmanager_csi: False # We deploy it unless set to False
      deploy_external_secrets: False
      deploy_cloudwatch_container_insights_metrics: True # We deploy it unless set to False
      deploy_cloudwatch_container_insights_logs: True
      cloudwatch_container_insights_logs_retention_days: 7
      deploy_amp: True
      deploy_grafana_for_amp: True
      deploy_kured: True
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
