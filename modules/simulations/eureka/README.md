
# examples/eureka


## Description
This module setups the environment for running robotic training and simulation.

- It creates a FSx static provisioning k8s resource
  - FSx is used as high performance data storage for storing training inputs/outputs
- It creates an IAM role for simulation
  - It allows pods to assume this role to get data from s3, FSx. Playing around with LLMs in Amazon Bedrock.
- It builds an application image
  - This will be a ROS2 image which contains necessary environment for training.
- It creates a Amazon SQS message queue
  - The queue is used control tasks sent by controller. The task controller will send tasks configs to the message queue and workers will get data from message queue.


## Inputs/Outputs

### Input Paramenters

#### Required
- `eks-cluster-admin-role-arn` - the role which creates the eks cluster
- `eks-cluster-name` - the name of the EKS cluster
- `eks-oidc-arn` - full ARN of the OIDC provider
- `eks-cluster-open-id-connect-issuer` - OIDC provider URI
- `application-ecr-name`: the name of the ecr which will store images containing simulation/training logics
- `sqs-name`: the name of the sqs we are creating
- `fsx-volume-handle`: file system id from the fsx created by dependency module
- `fsx-mount-point`: mount point of the fsx created by dependency module
- `data-bucket-name`: the name of the bucket which stores all simulation/trianing data

### Module Metadata Outputs

- `IamRoleArn`: IAM Role Arn which contains necessary permissions for EKS pods to assume and run simulation/training
- `ApplicationImageUri`: The application image which contains simulation/training logics and will be running in EKS
- `SqsUrl`: The url of the sqs which where task controllers will enqueue and workers will dequeue

#### Output Example

```json
{
    "IamRoleArn": "arn:aws:iam::123456789012:role/addf-eureka-simulation-role",
    "ApplicationImageUri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/robotic-applications:ubuntu-ros2",
    "SqsUrl": "https://sqs.us-west-2.amazonaws.com/123456789012/MyQueue"
}
