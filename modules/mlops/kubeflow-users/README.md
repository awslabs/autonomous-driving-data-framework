## Introduction
This module adds secured users to an implmententation of [Kubeflow](https://www.kubeflow.org/docs/) via [Kubeflow-on-AWS](https://awslabs.github.io/kubeflow-manifests/docs/).
It leverages the [Kubeflow-on-AWS github repo](https://github.com/awslabs/kubeflow-manifests) and the [Kubeflow-Manifests Github repo](https://github.com/kubeflow/manifests).




## Description

This module is meant to add users to a existing ADDF implementation of Kubeflow-On-AWS as denoted above.  It requires users to have all `Prerequisites` met prior to execution.  This is meant to support local development and does not expose ingresses to public DNS enpoints.

## Deployment 

### Prerequisites
This module requires BEFORE EXECUTION:
- EKS version 1.23 minimum
- the `kubeflow-platform` module deployed
- an AWS SecretsManager entry for EACH user already established
- the ARN of the policy to attach to each user
- an entry for each user in the module manifest under `KubeflowUsers` -- see `Input Parameters`

#### Using AWS SecretsManager
A unique entry to AWS SecretsManager for each user is required with the following JSON format:
```json
{
  "email": "user1@amazon.com",
  "password": "UniquePassword",
  "username": "user1"
}
```
In the above
  - an `email` address is required as this is the login for the user
  - a unique `password` is used to log into the dashboard 
  - the `username` becomes the namespace for this user - and should be all lowercase alpha-numeric characters.

A helper script is provided to seed this secret. 

This AWS SecretsManager entry MUST be created prior to running this module.

A script has been provided to create the secret entry:
`./modules/mlops/kubeflow-users/scripts/create_kf_user_secret.py --help`

The above command (without `--help`) will generate the AWS SecretsManager and add the proper message payload.

Kubeflow users can be added / removed from the deployment via the manifests.  A user email address and an IAM policy ARN are required.  Each user will have it's own password.  See `Reference Commands` to access the AWS SecretsManager for the user and view the password for access.   


### Accessing the cluster
This module currently does not deploy a public ingress to the dashboard (currently).  It is recommended to create a kubectl tunnel to the service and access the dashboard via `http://localhost:8080`.  See `Reference Commands`

## Inputs/Outputs


### Input Parameters


#### Required
- `EksClusterKubectlRoleArn` - the kubectl user in IAM that is the admin on the EKS cluster
- `EksClusterName` - the name of the EKS cluster
- `EksOidcArn` - full ARN of the OIDC provider
- `EksClusterOpenIdConnectIssuer` - OIDC provider URI
- `KubeflowUsers` - an array / list of entries with the two (2) elements for role creation
  -  `policyArn` - the ARN of an existing policy to attach to the role that are attached to the user pod
  -  `secret` - the name of the AWS SecretsManager entry that has the REQUIRED data fileds for each user to add to Kubeflow


#### Optional
None

#### Input Example
```yaml
  - name: EksClusterAdminRoleArn
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterAdminRoleArn
  - name: EksClusterName
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterName
  - name: EksOidcArn
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksOidcArn
  - name: EksClusterOpenIdConnectIssuer
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterOpenIdConnectIssuer
  - name: KubeflowUsers
    value:
    - policyArn: arn:aws:iam::aws:policy/AdministratorAccess
      secret: addf-mlops-kubeflow-users-user1
    - policyArn: arn:aws:iam::aws:policy/AdministratorAccess
      secret: addf-mlops-kubeflow-users-user2

```


### Module Metadata Outputs
- `EksClusterName` - the name of the EKS cluster these users are tied to
- `KubeflowUsers` - a stringifed list of dict's with :
  - `policyArn` - the policy ARN passed in tied to the newly created IAM role 
  - `secret` - the name of the AWS SecretsManager name tied to the newly created IAM role  
  - `roleArn` - the ARN of the the newly created role that the Kubeflow user will have attached to user pods in the user namespace
#### Output Example
```json
{
  "EksClusterName": "addf-mlops-core-eks-cluster",
  "KubeflowUsers": [
    {
      "policyArn": "arn:aws:iam::aws:policy/AdministratorAccess",
      "roleArn": "arn:aws:iam::123456789012:role/addf-mlops-users-kubeflow-users-us-east-1-0",
      "secret": "addf-mlops-kubeflow-users-user1"
    },
    {
      "policyArn": "arn:aws:iam::aws:policy/AdministratorAccess",
      "roleArn": "arn:aws:iam::123456789012:role/addf-mlops-users-kubeflow-users-us-east-1-1",
      "secret": "addf-mlops-kubeflow-users-user2"
    }
  ]
}

```



### Reference Commands

Be sure to have your `.kube/config` properly set up to access your cluster.  Here is a reference command, but you may use one that fits your cluster:
```bash
aws eks update-kubeconfig --name <clustername>
```

To tunnel to the cluster and access the dashboard over http://localhost:8080
```bash
kubectl port-forward svc/istio-ingressgateway -n istio-system 8080:80
```

To fetch the secrets information:
```bash
aws secretsmanager get-secret-value \
--secret-id <secretname> \
--query SecretString \
--output text \
--region <region> | jq -r
```
