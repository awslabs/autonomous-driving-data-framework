## Introduction
This is an implmententation of [Kubeflow](https://www.kubeflow.org/docs/) via [Kubeflow-on-AWS](https://awslabs.github.io/kubeflow-manifests/docs/).
It leverages the [Kubeflow-on-AWS github repo](https://github.com/awslabs/kubeflow-manifests) and the [Kubeflow-Manifests Github repo](https://github.com/kubeflow/manifests).




## Description

This is a seedfarmer / ADDF wrapped implementation based off Kubeflow-on-AWS.  This allows customization of the deployment via the module's `deplopyspec`.
It currently supports only the following:
- `vanilla` deployment via the `kustomize` deployment method
- Kubeflow v1.6.1
- AWSKubebuild 1.0.0

*** NOTE: this module does not support earlier versions of Kubeflow v1.6.1 as specified in the branches of [Kubeflow-on-AWS](https://github.com/awslabs/kubeflow-manifests)

Since this module is extenisble, additions and modifications are encouraged.



## Prerequisites
This module depends on an existing EKS cluster and access to EKS Master role (an IAM role that is an admin on the EKS cluster and has IAM capabilty to create/delete roles and policies).

<b>The EKS cluster version MUST be at least 1.23</b>



## Inputs/Outputs


### Input Parameters


#### Required
- `EksClusterMasterRoleArn` - the masterrole in IAM that was used to create the EKS cluster
- `EksClusterName` - the name of the EKS cluster
- `InstallationOption` - should be `kustomize` 
- `DeploymentOption` - please see [Deployment Options](https://awslabs.github.io/kubeflow-manifests/docs/deployment/)
  - only `vanilla` is currently supported
- `KubeflowReleaseVersion` - only v1.6.1 currently tested
  - please see [Release Versions](https://awslabs.github.io/kubeflow-manifests/docs/about/releases/)
- `AwsKubeflowBuild` - 1.0.0 currently tested
  - please see [Build Versions](https://awslabs.github.io/kubeflow-manifests/docs/about/releases/)
  - **** this must be a string element ---> \`1.0.0\`

#### Optional
- `NvidiaDevicePluginVersion` - the version of the NVIDIA plugin to allow EKS to recognize GPU compute
  - this is set to `0.13.0` by default and is the RECOMMENDED version - override at your own risk!
  - ref [NVIDIA Plugin Repo](https://github.com/NVIDIA/k8s-device-plugin)

#### Input Example
```yaml
  - name: EksClusterMasterRoleArn
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterMasterRoleArn
  - name: EksClusterName
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterName
  - name: InstallationOption
    value: kustomize
  - name: DeploymentOption
    value: vanilla
  - name: KubeflowReleaseVersion
    value: v1.6.1
  - name: AwsKubeflowBuild
    value: '1.0.0'

```


### Module Metadata Outputs
- `EksClusterName` - the name of the EKS cluster this Kubeflow platform is deployed on

#### Output Example
```json
{
  "EksClusterName": "addf-mlops-core-eks-cluster"
}

```


