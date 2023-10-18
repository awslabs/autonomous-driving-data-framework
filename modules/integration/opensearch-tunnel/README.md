# Opensearch Tunnel


## Description

This module creates an EC2 instance to act as a proxy for the OpenSearch Cluster with an NGINX server.  It uses the [AWS SSM Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html) to securely tunnel to the instance and give access to the OpenSearch Dashboard.


The EC2 instance is deployed in a private subnet that must have Internet Access configured via a NAT Gateway in th VPC.

### Prerequisistes

A VPC with a NAT Gateway installed.
The [AWS SSM Plugin for AWS CLI](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)

## Inputs/Outputs

### Input Paramenters

#### Required

- `opensearch-sg-id`: The security group id of the OpenSearch cluster
- `opensearch-domain-endpoint`: The OpenSearch Domain endpoint
- `vpc-id`: The VPC-ID that the cluster will be created in

#### Optional
- `port` - the port the NGINX server listens on 
  - defaults to `3000`
- `solution-id`: a unique identifier for this deployment (must be used with `solution-description`)
- `solution-name`: a unique name for this deployment (must be used with `solution-id`)
- `solution-version`: a unique version for this deployment

The parameters `(solution-*)` will resolve a custom text that is used as a description of the stack if populated.

### Module Metadata Outputs
- `OpenSearchTunnelDNS`: the public DNS of the instance
- `OpenSearchTunnelIP`: the public IP of the instance
- `OpenSearchTunnelUrl`: the URL of the dashboard this server is proxying
- `SampleSSMCommand` an example command to execute the tunnel to the EC2 instance 
  - NOTE: the `--parameters` command will have to be altered to properly implement quotes around the values (ie. remove the escaping backslashes `\`)


#### Output Example
```json
{
  "OpenSearchTunnelInstanceId": "i-0347c41eb54ced515",
  "OpenSearchTunnelUrl": "http://localhost:3333/_dashboards/",
  "OpenSearchTunnelPort": 3333,
  "SampleSSMCommand": "aws ssm start-session --target i-0347c41eb54ced515 --document-name AWS-StartPortForwardingSession --parameters '{\"portNumber\": [\"3333\"], \"localPortNumber\": [\"3333\"]}'"
}

```
