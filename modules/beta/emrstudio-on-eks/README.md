# EMR Studio

[Reference](https://aws.amazon.com/blogs/big-data/configure-amazon-emr-studio-and-amazon-eks-to-run-notebooks-with-amazon-emr-on-eks/)

## Description

This module deploys EMR Studio with EMR on EKS as the backend using AWS SSO for Authentication.

Enabling AWS SSO is a prerequisite:

- Enable AWS SSO in the same Region where the EMR Studio resides.
- If the account is part of an organizational account, AWS SSO needs to be enabled in the primary account.
- Enable AWS SSO and set up users in AWS SSO. For instructions, see [Getting Started](https://docs.aws.amazon.com/singlesignon/latest/userguide/getting-started.html) and [How to create and manage users within AWS Single Sign-On](https://aws.amazon.com/blogs/security/how-to-create-and-manage-users-within-aws-sso/).
- Capture the user you have creatd using AWS SSO, populate the attribute `sso-username` with its value and provide it as an input in the below manifest file to deploy `emrstudio`

#### Required

- `vpc-id`: The VPC-ID that the cluster will be created in
- `private-subnet-ids`: The Private Subnets that the AWS Batch Compute resources will be deployed to
- `eks-cluster-admin-role-arn`: The EKS Cluster's Admin Role Arn obtained from EKS Module metadata
- `eks-cluster-name`: The EKS Cluster Name obtained from EKS Module metadata
- `eks-oidc-arn`: The EKS Cluster's OIDC Arn for creating EKS Service Accounts obtained from EKS Module metadata
- `eks-openid-issuer`: The EKS Cluster's OPEN ID issuer
- `artifact-bucket-name`: The Artifact bucket to which EMR Studio will be using for backing up Workspaces and notebook files
- `sso-username`: The UserName added to the AWS SSO which will be integrated as the mode of authentication to create EMR Workspace(s)

#### Optional

- `emr-eks-namespace`: The EKS Namespace to which the Virtual Cluster should be deployed to.

#### Sample Manifest to deploy EMRStudio

```yaml
name: emrstudio-on-eks
path: modules/ide/emrstudio-on-eks/
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
  - name: logs-bucket-name
    valueFrom:
      moduleMetadata:
        group: optionals
        name: datalake-buckets
        key: LogsBucketName
  - name: sso-username
    value: ssriche
  - name: emr-eks-namespace
    value: emr-studio
```

#### Issues to know about EMR Studio during CLEANUP Workflow

- There is no current mechanism to delete the EMR Workspace(s) using API calls (Boto3/CLI) which is needed before you delete Virtual Clusters. You would need to delete them using AWS Console before proceeding with the deletion of EMRStudio module.
- There is a known issue during cleanup workflow, where the managed endpoints will be stuck in `TERMINATING` phase and the VirtualCluster deletion will be blocked further blocking the deletion of EMRStudio CDK Stacks.

### Module Metadata Outputs

- `StudioUrl`: the EMR Studio URL using which we create EMR Workspaces by authenticating using the `username` created in AWS SSO

#### Output Example

```json
{
    "StudioUrl":"https://es-XXXXXXXXXX.emrstudio-prod.us-west-2.amazonaws.com",
}
