# DDB to OpenSearch


## Description

This module create a Lambda in a private subnet to read from an existing DDB Stream and write to 
an existing OpenSearch Domain

## Inputs/Outputs

### Input Paramenters

#### Required

- `opensearch-sg-id`: The security group id of the OpenSearch cluster
- `opensearch-domain-endpoint`: The OpenSearch Domain endpoint
- `opensearch-domain-name`: The OpenSearch Domain name
- `vpc-id`: The VPC-ID that the cluster will be created in
- `rosbag-stream-arn`: the ARN of the ddb stream connected to the rosbag metadata table (to be indexed)
- `private-subnet-ids`: the private subnets the lambda should run in, as a stringifed array list

#### Optional

### Module Metadata Outputs

#### Output Example
