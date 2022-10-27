# Dev-Intance

## Description
This module will deploy an EC2 instance with an Ubuntu Desktop reachable via NiceDCV.  It is intended for GPU compute, but can run on CPU compute (with limitations)

It has installed:
 - Ubuntu 20.04 Server Desktop
 - NiceDCV
 - Chrome
 - FoxGlove
 - Ros Noetic
 - Gazebo
 - RViz
 - Jupyter

It leveages AWS SecretsManager to store the username and password to acces the instance via a browser.  We dynamically generate a unique password for you.  


The user is ALWAYS `ubuntu`.

### Custom File Support
Any file you want staged on the running instance should be saved in the `scripts/` directory of this code module.  All files placed in this directory will be copied to the running EC2 instance located at the `/home/ubuntu/scripts` directory and accessible by the `ubuntu` user.

## Inputs/Outputs


### Input Parameters


#### Required
- `vpc-id` - the VPC this instance will reside in --- MUST have public subnets


#### Optional
- `instance-type` - the type of EC2 compute to use - defaults to `g4dn.xlarge`
- `s3-script-bucket` - a place to stage any scripts that will be put on the ubuntu users home directory
  - This MUST be a bucket in the project (ex. `addf-`)
- `s3-dataset-bucket` - any staged datasets that the server needs access to
- `ami-id` - if there is a preferred Ubuntu 20.04 Server to use, otherwise we will pick the optimal one
- `demo-password` - implement a defined password
  - ******  CAUTION  ****** this is to be used ONLY for demo purposes and not with sensitive data.  DO NOT USE with any critical or in sensitive environments / infrastructures!!!!  You have been warned...

#### Input Example
```yaml
parameters:
  - name: vpc-id
    valueFrom:
      moduleMetadata:
        group: optionals
        name: networking
        key: VpcId
  - name: instance-type
    value: g4dn.xlarge
  - name: s3-script-bucket
    valueFrom:
       moduleMetadata:
        group: optionals
        name: datalake-buckets
        key: ArtifactsBucketName
```

### Module Metadata Outputs
- `DevInstanceURL` - the url with port to access the  NiceDCV endpoint
- `AWSSecretName` - the name of the AWS SecretsManager entry that has the password 


#### Output Example
```json
{
    "AWSSecretName": "addf-dataservice-visualization-dev-instance-0-ubuntu-password", 
    "DevInstanceURL": "https://ec2-34-229-76-152.compute-1.amazonaws.com:8443"
}
```

### Helpful commands

`seedfarmer list moduledata -d dataservice -g visualization -m dev-instance`

```bash
aws secretsmanager get-secret-value \
    --secret-id <secretname> \ 
    --query SecretString \
    --output text \
    --region "$AWS_REGION" | jq -r 
```
