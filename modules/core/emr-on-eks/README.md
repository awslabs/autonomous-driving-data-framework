## Introduction

This module provisions EMR on EKS supporting infrastructure which creates EMR Vritual Cluster, K8s Namespace, EMR Job Execution Role which enables any spark applications to use Airflow to trigger spark jobs on EMR on EKS.

> Note: You should be adjusting the required permissions on EMR Job execution role to allow spark driver to write logs to CloudWatch and S3 logging bucket.

## Inputs/Outputs

### Input Parameters

#### Required

- `vpc-id`: The VPC-ID that the cluster will be created in
- `private-subnet-ids`: The Private Subnets that the AWS Batch Compute resources will be deployed to
- `eks-cluster-admin-role-arn`: The EKS Cluster's Admin Role Arn obtained from EKS Module metadata
- `eks-cluster-name`: The EKS Cluster Name obtained from EKS Module metadata
- `eks-oidc-arn`: The EKS Cluster's OIDC Arn for creating EKS Service Accounts obtained from EKS Module metadata
- `eks-openid-issuer`: The EKS Cluster's OPEN ID issuer
- `raw-bucket-name`: The Raw bucket to which the test dataset `citi-ride` of NY will be uploaded, converted to parquet - sample spark use-case used to demo the module.
- `dag-bucket-name`: name of the Bucket configured in the shared MWAA Environment to store DAG artifacts
- `dag-path`: name of the path in the Bucket configured in the shared MWAA Environment to store DAG artifacts
- `mwaa-exec-role`: ARN of the MWAA Execution Role
- `emr-eks-namespace`: The EKS Namespace to which the Virtual Cluster should be deployed to.

#### Optional

### Sample declaration of Airflow with EMR on EKS

```yaml
name: emr-on-eks
path: modules/core/emr-on-eks/
parameters:
  - name: vpc-id
    valueFrom:
      moduleMetadata:
        group: optionals
        name: networking
        key: VpcId
  - name: private-subnet-ids
    valueFrom:
      moduleMetadata:
        group: optionals
        name: networking
        key: PrivateSubnetIds
  - name: eks-cluster-admin-role-arn
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterAdminRoleArn
  - name: eks-cluster-name
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterName
  - name: eks-oidc-arn
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksOidcArn
  - name: eks-openid-issuer
    valueFrom:
      moduleMetadata:
        group: core
        name: eks
        key: EksClusterOpenIdConnectIssuer
  - name: artifact-bucket-name
    valueFrom:
      moduleMetadata:
        group: optionals
        name: datalake-buckets
        key: ArtifactsBucketName
  - name: airflow-emr-eks-namespace
    value: emr-eks-spark
  - name: dag-path
    valueFrom:
      moduleMetadata:
        group: core
        name: mwaa
        key: DagPath
  - name: mwaa-exec-role
    valueFrom:
      moduleMetadata:
        group: core
        name: mwaa
        key: MwaaExecRoleArn
  - name: raw-bucket-name
    valueFrom:
      moduleMetadata:
        group: optionals
        name: datalake-buckets
        key: RawBucketName
  - name: logs-bucket-name
    valueFrom:
      moduleMetadata:
        group: optionals
        name: datalake-buckets
        key: LogsBucketName
```

### Module Metadata Outputs

- `EmrJobExecutionRoleArn`: ARN for the EMR On EKS Execution Role
- `VirtualClusterId`: Cluster ID for the EMR Virtual Cluster ID

#### Output Example

EksRbacStack:

```json
{
    "EmrJobExecutionRoleArn":"arn:aws:iam::1234567890:role/addf-demo-simulations-emr-XXXXXXXX"
}
```

EMRStack:

```json
{
    "VirtualClusterId":"ncXXXXXXXX"
}