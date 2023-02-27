# Service Catalog Module

## Description

This module creates Service catalog portfolio together with Custom SageMaker project template from seed code.

## Inputs/Outputs


### Input Parameters


#### Required


#### Optional
- `portfolio_access_role_arn`: role that should be granted access to service catalog. To see SageMaker custom project template, role used for SageMaker studio needs to be granted access to portfolio



### Module Metadata Outputs
- PortfolioARN
- PortfolioAccessRoleARN
- PortfolioAccessRoleName


#### Output Example
```yaml
{
  "PortfolioARN": "arn:aws:servicecatalog:us-east-1:xxxxxxxxxxxx:portfolio/port-hl6pznl5rjkls",
  "PortfolioAccessRoleARN": "arn:aws:iam::xxxxxxxxxxxx:role/addf-mlops-sagemaker-sage-smrolesleaddatascientist-O5OLKFYVYA75",
  "PortfolioAccessRoleName": "addf-mlops-sagemaker-sage-smrolesleaddatascientist-O5OLKFYVYA75"
}
```