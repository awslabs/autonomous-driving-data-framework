## Introduction
This is an implmententation of [Kubeflow](https://www.kubeflow.org/docs/) via [Kubeflow-on-AWS](https://awslabs.github.io/kubeflow-manifests/docs/).
It leverages the [Kubeflow-on-AWS github repo](https://github.com/awslabs/kubeflow-manifests) and the [Kubeflow-Manifests Github repo](https://github.com/kubeflow/manifests).




## Description

This is a seedfarmer / ADDF wrapped implementation based off Kubeflow-on-AWS.  This allows customization of the deployment via the module's `deplopyspec`.
It currently supports only the following:
- `vanilla` deployment via the `kustomize` deploymetn method
- Kubeflow v1.6.1
- AWSKubebuild 1.0.0

Since this module is extenisble, addition and modifications are encouraged.



## Deployment
This module depends on an existing EKS cluster and access to EKSKubectl Admin role.  OIDC support can be added in as needed - but is not currently needed.

Kubeflow users can be added / removed from the deployment via the manifests.  A user email address and an IAM policy ARN are required.  The module will create
a new AWS SecretsManager entry with an auto-genrated password for that user.  Each user will have it's own password.  See `Reference Commands` to access the AWS SecretsManager for the user and view the password for access.   If you want to change the password to a custom value, you will need to modify the AWS SecretsManager entry directly and redeploy the module so the password can be referenced by the cluster (securely)


### Accessing the cluster
This module currently does not deploy a public ingress to the dashboard (currently).  It is recommended to create a kubectl tunnel to the service and access the dashboard via `http://localhost:8080`.  See `Reference Commands`

## Inputs/Outputs


### Input Parameters


#### Required
- `EksClusterKubectlRoleArn` - the kubectl user in IAM that is the admin on the EKS cluster
- `EksClusterName` - the name of the EKS cluster
- `InstallationOption` - should be `kustomize` 
- `DeploymentOption` - please see [Deployment Options](https://awslabs.github.io/kubeflow-manifests/docs/deployment/)
  - only `vanilla` is currently supported
- `KubeflowReleaseVersion` - only v1.6.1 currently tested
  - please see [Release Versions](https://awslabs.github.io/kubeflow-manifests/docs/about/releases/)
- `AwsKubeflowBuild` - 1.0.0 currently tested
  - please see [Build Versions](https://awslabs.github.io/kubeflow-manifests/docs/about/releases/)
  - **** this must be a string element ---> `1.0.0`
- `KubeflowUsers` - 
  -  `email` - the email address that a user will sign in with. A username for the Namespace will be derived from the email address
  -  `policyArn` - the ARN of an existing polocy to attach to the pod

#### Optional


#### Input Example
```yaml
  - name: EksClusterKubectlRoleArn
    valueFrom:
      moduleMetadata:
        group: core
        name: eksagain
        key: EksClusterKubectlRoleArn
  - name: EksClusterName
    valueFrom:
      moduleMetadata:
        group: core
        name: eksagain
        key: EksClusterName
  - name: InstallationOption
    value: kustomize
  - name: DeploymentOption
    value: vanilla
  - name: KubeflowReleaseVersion
    value: v1.6.1
  - name: AwsKubeflowBuild
    value: '1.0.0'
  - name: KubeflowUsers
    value:
    - email: someuser@amazon.com
      policyArn: arn:aws:iam::123456789012:role/AdminRole
    - email: another.user@gmail.com
      policyArn: arn:aws:iam::123456789012:role/AdminRole

```


### Module Metadata Outputs
- `KubeflowUsersDeployed` - a stringifed dict of the users deployed with the username as the key and the usename, email and AWS SecretsManager names for reference


#### Output Example
```json
{
  "KubeflowUsers": {
    "someuser": {
      "email": "someuser@amazon.com",
      "secretname": "addf-dataservice-ml-kubeflow-kf-someuser",
      "username": "someuser"
    },
    "anotheruser": {
      "email": "another.user@gmail.com",
      "secretname": "addf-dataservice-ml-kubeflow-kf-anotheruser",
      "username": "anotheruser"
    }
  }
}

```



### Reference Commands
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
