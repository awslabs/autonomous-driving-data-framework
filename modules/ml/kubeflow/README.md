## Introduction
kubeflow


## Description

A short description of the module.

## Architecture



## Deployment


## Inputs/Outputs


### Input Parameters


#### Required


#### Optional
- `EksClusterKubectlRoleArn`
- `EksClusterName`
- `InstallationOption` - should be `kustomize` - can be `helm`
- `DeploymentOption` 
- `KubeflowReleaseVersion`
- `AwsKubeflowBuild`
- `KubeflowUsers`

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
    - email: anotheruser@gmail.com
      policyArn: arn:aws:iam::123456789012:role/AdminRole
    - email: thirduser@gmail.com
      policyArn: arn:aws:iam::123456789012:role/AdminRole
```


### Module Metadata Outputs



#### Output Example




### Reference Commands
kubectl port-forward svc/istio-ingressgateway -n istio-system 8080:80
kubectl apply -f <directory>
