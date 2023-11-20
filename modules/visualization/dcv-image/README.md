
# dcv-image


## Description

This module:

- Creates an ECR repo which stores the dcv image.
- Builds the image which will be used as the DCV server.
- This module does not depend on other modules to build.

## Inputs/Outputs

### Input Paramenters

#### Required
- `eks-dcv-repo-name`: a unique name for ECR repo to store dcv image.

#### Optional

- `solution-id`: a unique identifier for this deployment (must be used with `solution-description`)
- `solution-name`: a unique name for this deployment (must be used with `solution-id`)
- `solution-version`: a unique version for this deployment

The parameters `(solution-*)` will resolve a custom text that is used as a description of the stack if populated. 
### Module Metadata Outputs

- `DCVImageRepoUri`: Uri of ECR repo to store dcv image.

#### Output Example

```json
{
    "DCVImageRepoUri": ECR repo to store dcv image.
}



