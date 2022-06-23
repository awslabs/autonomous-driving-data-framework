# Security-Groups


## Description

This module modifies security groups of EKS and OpenSearch AWS resources, allowing ingress of traffic and configuring fluent-bit helm charts to write to OS domain

## Inputs/Outputs

### Input Paramenters

#### Required

- `opensearch-sg-id`: The security group id of the OpenSearch cluster obtained from `opensearch` Module metadata
- `opensearch-domain-endpoint`: The OpenSearch Domain endpoint from `opensearch` Module metadata
- `eks-cluster-admin-role-arn`: The EKS Cluster's Admin Role Arn obtained from EKS Module metadata
- `eks-cluster-name`: The EKS Cluster Name obtained from EKS Module metadata
- `eks-cluster-sg-id`: The EKS Cluster's Security Group ID obtained from EKS Module metadata
- `eks-oidc-arn`: The EKS Cluster'd OIDC Arn for creating EKS Service Accounts obtained from EKS Module metadata

#### Optional

### Module Metadata Outputs

- `OpenSearchProxyDNS`: the public DNS of the instance
- `OpenSearchProxyIP`: the public IP of the instance
- `OpenSearchProxyUrl`: the URL of the dashboard this server is proxying

#### Output Example

```json
{
    "OpenSearchProxyDNS":"ec2-18-212-202-77.compute-1.amazonaws.com",
    "OpenSearchProxyIP":"18.212.202.77",
    "OpenSearchProxyUrl":"https://ec2-18-212-202-77.compute-1.amazonaws.com/_dashboards/",
}


