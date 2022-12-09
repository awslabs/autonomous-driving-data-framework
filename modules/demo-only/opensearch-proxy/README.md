# Security-Groups


## Description

This module creates an EC2 instance to act as a proxy for the OpenSearch Cluster.  It is using basic authentication for access, which can be viewed in the `moduledata`.

### Prerequisistes

A username and password is required to access the IDE, stored in `AWS Secrets Manager` with the below json representation:

```json
{
    "username": "theusername",
    "password": "testpassword"
}
```

The name of the  `AWS Secrets Manager`  is a parameter that is passed in to ADDF.

<b> CURRENTLY this module only supports alpha-numeric charaacters in the password </b>

## Inputs/Outputs

### Input Paramenters

#### Required

- `opensearch-sg-id`: The security group id of the OpenSearch cluster
- `opensearch-domain-endpoint`: The OpenSearch Domain endpoint
- `vpc-id`: The VPC-ID that the cluster will be created in
- `secrets-manager-name`: Name of the OpenSearchProxy secret created in SecretsManager
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

```
