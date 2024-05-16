# Dev-Intance

## Description
This module will deploy an EC2 instance with an Ubuntu Desktop reachable via NiceDCV.  It is intended for GPU compute, but can run on CPU compute (with limitations)

By default it has installed:
- Ubuntu 20.04 Server Desktop
- NiceDCV
- Chrome
- FoxBox
- ROS Noetic
- Gazebo
- RViz
- Jupyter

It leverages AWS SecretsManager to store the username and password to acces the instance via a browser.  During deployment an unique password is generated.  

The user is ALWAYS `ubuntu`.

### Custom File Support
Any file you want staged on the running instance should be saved in the `scripts/` directory of this code module.  All files placed in this directory will be copied to the running EC2 instance located at the `/home/ubuntu/scripts` directory and accessible by the `ubuntu` user.

## Inputs/Outputs

### Input Parameters

#### Required
- `vpc-id` - the VPC this instance will reside in --- MUST have public subnets

#### Optional
- `instance-type` - the type of EC2 compute to use - defaults to `g4dn.xlarge`
- `instance-count` - the number (INT) of identical instances to create with the same security group and same instance profile
  - defaults to 1
- `s3-bucket-scripts` - a place to stage any scripts that will be put on the ubuntu users home directory
  - This MUST be a bucket in the project (ex. `addf-`)
- `s3-bucket-dataset` - any staged datasets that the server needs access to
- `ami-id` - An AMI Id if there is a preferred Ubuntu 20.04 Server to use. It can be set to the values "focal" or "jammy" to use the selected distribution (Leaving it empty will select "focal" latest by default)
- `demo-password` - implement a defined password
  - ******  CAUTION  ****** this is to be used ONLY for demo purposes and not with sensitive data. DO NOT USE with any critical or in sensitive environments / infrastructures!!!!  You have been warned...

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
  - name: instance-count
    value: 2
  - name: ami-id
    value: "focal"
  - name: s3-bucket-dataset
    valueFrom:
       moduleMetadata:
        group: optionals
        name: datalake-buckets
        key: ArtifactsBucketName
```

### Module Metadata Outputs
Nested in the instance indicator, there are two pertinent parameters output:
- `DevInstanceURL` - the url with port to access the  NiceDCV endpoint
- `AWSSecretName` - the name of the AWS SecretsManager entry that has the password 

Thr structure is:
- dev-instance-name
  - `DevInstanceURL`
  - `AWSSecretName`


#### Output Example
```json
  {
    "dev-instance-0": {
      "AWSSecretName": "addf-dataservice-visualization-dev-instance-0-ubuntu-password",
      "DevInstanceURL": "https://ec2-3-90-103-67.compute-1.amazonaws.com:8443"
    },
    "dev-instance-1": {
      "AWSSecretName": "addf-dataservice-visualization-dev-instance-1-ubuntu-password",
      "DevInstanceURL": "https://ec2-54-91-11-227.compute-1.amazonaws.com:8443"
    },
    "dev-instance-2": {
      "AWSSecretName": "addf-dataservice-visualization-dev-instance-2-ubuntu-password",
      "DevInstanceURL": "https://ec2-54-221-109-36.compute-1.amazonaws.com:8443"
    }
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
