# Deploying JupyterHub


## Description

This module deploys `JupyterHub` environment onto the Amazon EKS Cluster.
> This is not a production ready `JupyterHub` environment, as it currently runs on port 80.

### Prerequisistes

You should be creating `JupyterHub` user credentials as a secret in AWS Secrets Manager with the below json representation:

```json
{"username": "testadmin", "password": "testpassword"}
```

#### Required

- `eks-cluster-name`: The EKS Cluster Name obtained from EKS Module metadata
- `eks-cluster-admin-role-arn`: The EKS Cluster's Master Role Arn from EKS Module metadata
- `eks-oidc-arn`: The EKS Cluster'd OIDC Arn for creating EKS Service Accounts obtained from EKS Module metadata
- `secrets-manager-name`: Name of the JupyterHub secret created in SecretsManager

#### Optional


### Module Metadata Outputs

Then you can query the DNS Name of the JupyterHub ingress using the below command and log into the JupyterHub environment, where you would need to provide the username and password (values configured in the AWS Secrets Manager above):

```sh
echo $(kubectl get ing jupyterhub -n jupyter-hub -o jsonpath="{.status.loadBalancer.ingress[0].hostname}")/jupyter
```

#### Output Example

"k8s-jupyterh-jupyterh-XXXXXX.us-west-2.elb.amazonaws.com/jupyter"

#### Demo the WebViz Module

- The private RestAPI endpoint URL can be obtained from the output of `WebViz` CloudFormation stack metadata which will be in the following sample format:

> Example: "https://XXXXXXXXX.execute-api.us-west-2.amazonaws.com/get-url?"

- Then, you would need to have `scene_id` and `record_id` handy which can be obtained from the `scene-metadata` dynamodb table

- From the logged in environment of JH, open a terminal and run the below command:

```sh
wget -qO- "https://f1hdrfo4j2.execute-api.us-west-2.amazonaws.com/get-url?scene_id=<<SCENE_ID>>&record_id=<<RECORD_ID>>"
```

> Note: `SCENE_ID` and `RECORD_ID` are the query string parameters which you would need to replace when you run the above command.
