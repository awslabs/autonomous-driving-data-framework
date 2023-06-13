# Deploying VSCode IDE on EKS

## Description

This module deploys VSCode IDE onto the Amazon EKS Cluster. See here for:

- [git repo](https://github.com/coder/code-server)
- [helm-chart reference](https://coder.com/docs/code-server/latest/helm)
  > This is not a production ready `VSCode` IDE, as it currently runs on port 80. Use at your own risk (for now).

### Prerequisistes

A password is required to access the IDE, stored in `AWS Secrets Manager` with the below json representation:

```json
{ "password": "testpassword" }
```

The name of the `AWS Secrets Manager` is a parameter that is passed in to ADDF.

#### Required

- `eks-cluster-name`: The EKS Cluster Name obtained from EKS Module metadata
- `eks-cluster-admin-role-arn`: The EKS Cluster's Master Role Arn obtained from EKS Module metadata
- `eks-oidc-arn`: The EKS Cluster'd OIDC Arn for creating EKS Service Accounts obtained from EKS Module metadata
- `secrets-manager-name`: Name of the VSCode secret created in SecretsManager

#### Optional

### Module Metadata Outputs

Then you can query the DNS Name of the VSCode ingress using the below command:

```sh
$ echo $(kubectl get ing code-server -n code-server -o jsonpath="{.status.loadBalancer.ingress[0].hostname}")/code-server
```

#### Output Example

k8s-codeserv-codeserv-XXXXXXXXXXXX.us-east-1.elb.amazonaws.com/code-server
