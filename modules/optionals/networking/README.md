# Networking Module

## Description

This module creates netowrking resources to support ADDF.  It is not required as 
modules can leverage existing VPC networks.

This module:
- creates networking resources to support ADDF
  - VPC and Subnets
  - VPC Endpoints
  - module-specific role with least privileges policy
- exports Metadata by setting the `ADDF_MODULE_METADATA` env var on completion


##### Please provide `deployspec.yaml` and `modulestack.yaml` files which will be consumed by SeedFarmer CLI.

## Inputs/Outputs

### Input Paramenters
None

#### Required

None

#### Optional

- `internet-accessible`: a boolean flag indicating whether or not the subnets have internet access.
  - `True` or `False` 
  - Assumed to be True

### Module Metadata Outputs

- `VpcId`: The VPC ID created
- `PublicSubnetIds`: An array of the public subnets 
- `PrivateSubnetIds`: An array of the private subnets 
- `IsolatedSubnetIds`: An array of the isolated subnets  (only if `internet-accessible` is `False`)


#### Output Example

```json
{
  "IsolatedSubnetIds": [],
  "PrivateSubnetIds": ["subnet-1234567890abc", "subnet-1234567890def"],
  "PublicSubnetIds": ["subnet-1234567890ghi", "subnet-1234567890jkl"],
  "VpcId": "vpc-1234567890mno"
}
```
