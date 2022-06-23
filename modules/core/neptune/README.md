# Neptune


## Description

This module creates a Neptune cluster for use in ADDF


## Inputs/Outputs

### Input Paramenters

#### Required

- `vpc-id`: The VPC-ID that the cluster will be created in

#### Optional
- `number-instances`: The number of compute nodes, defaults to `2`


### Module Metadata Outputs

- `NeptuneClusterId`: the id of the Neptune Cluster
  `NeptuneEndpointAddress`: the address of the Neptune Cluster Endpoint- for inserting data and reading
- `NeptuneReadEndpointAddress`: the address of the Neptune Cluster REad-Only Endpoint
- `NeptuneSecurityGroupId`: the id of the Security Group on the Cluster

#### Output Example

```json
{
    "NeptuneClusterId": "addf-test-core-neptuneCluster",
    "NeptuneEndpointAddress": "addf-test-core-neptunecluster.cluster-cf6xovvml17s.us-east-1.neptune.amazonaws.com:8182",
    "NeptuneReadEndpointAddress": "addf-test-core-neptunecluster.cluster-ro-cf6xovvml17s.us-east-1.neptune.amazonaws.com:8182",
    "NeptuneSecurityGroupId": "sg-0605123720caec685"
}