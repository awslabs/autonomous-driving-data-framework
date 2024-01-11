
# DCV-EKS Module

## Description
This module creates necessary resources for DCV server to work. It is 
implemented in a fashion of one DCV server per K8S worker node (using a 
DaemonSet). User needs to use the IP address of the node to connect to the 
DCV  server. This module will open a NodePort for users to connect and 
forward the traffic to DCV server. This module will also output necessary 
information (display number and local mounting path) to configmap and aws 
ssm parameter store. There will also be failure handling in DCV image. DCV 
container will be restarted if the health check fails. The DCV session 
configurations are outlined in dcv-image module.

For user application pods to stream, user need to have two required inputs 
to their pods:
1. `DISPLAY` environment variable: usually the value is `:0`, but it is not 
   guaranteed. User could check the actual display value in K8S ConfigMap 
   `dcv::dcv-agent-config-map`. The value could be acquired via either of 
   the following commands: 
   1. `kubectl get cm dcv-agent-config-map -n dcv -o "jsonpath={.data['display']}"`
   2. `aws ssm get-parameter --name /addf/mlops/dcv-eks-dcv-eks/dcv-display --query "Parameter.Value" --output text`
2. Local mount shared drive: DCV will create a display socket. The DCV pod 
   will use local mount to share the display socket. For user application 
   pods, they will have to mount the shared directory in the node using 
   local mount. Default value is `/var/addf/dcv-eks/sockets`. User could 
   also check the actual value in K8S ConfigMap `dcv::dcv-agent-config-map`. 
   The value could be acquired via either of the following commands: 
   1. `kubectl get cm dcv-agent-config-map -n dcv -o "jsonpath={.data['socket_mount_path']}"`
   2. `aws ssm get-parameter --name /addf/mlops/dcv-eks-dcv-eks/dcv-socket-mount-path --query "Parameter.Value" --output text`

In summary, this module creates the following resources
- Updates EKS node role to include permissions to access DCV license in S3
- Updates security groups of the nodes to allow ingress traffic (TCP and UDP) to specific DCV nodeport
- Creates a role for DCV pods to access AWSSecretsManager and kubernetes resources
- Creates necessary k8s resources:
  - Role: for DCV pods to manage specific k8s resources
  - ServiceAccount: for DCV pods to assume IAM role and k8s role
  - RoleBinding: to bind k8s role to the k8s service account
  - ConfigMap: to store dcv runtime output, such as `display` and `socket_path` which application pods will be using to render applications
  - Service: NodePort service to open port on each node and forward traffic locally to the DCV pod
  - DaemonSet: daemonset for dcv containers which also include failure handling

## Deployment
### Prerequisites
- AWS SecretsManager entries for username `dcv-cred-user` and password `dcv-cred-passwd` already established

#### Using AWS SecretsManager
The key `dcv-cred-user` and `dcv-cred-passwd` need to exist in AWS SecretsManager.

## Inputs/Outputs

### Input Paramenters

#### Required

- `dcv-image-uri` - DCV container image uri
- `eks-cluster-admin-role-arn` - the role which creates 
  the eks cluster
- `eks-cluster-name` - the name of the EKS cluster
- `eks-oidc-arn` - full ARN of the OIDC provider
- `eks-cluster-open-id-connect-issuer` - OIDC 
  provider URI
- `eks-cluster-security-group-id` - id of security 
  group which is attached to all nodes in eks
- `eks-node-role-arn` - arn of the role which is attached to all 
  nodes in eks

#### Optional
- `dcv-namespace`: the namespace to store all DCV related 
  resources. Defaults to `dcv`.
- `dcv-nodeport`: the nodeport which will be used by nodeport 
  service. Defaults to `31980`.

### Module Metadata Outputs

- `DcvEksRoleArn`: arn of the role 
- `DcvNamespace`: the namespace to create all DCV resources
- `DcvNodeport`: port number of the DCV Nodeport service
- `DcvDisplayParameterName`: SSM parameter name for display number
- `DcvSocketMountPathParameterName`: SSM parameter name for shared directory path in worker node

#### Output Example

```json
{
    "DcvEksRoleArn": "arn:aws:iam::XXXXXXXX:role/DcvEksRole",
    "DcvNamespace": "dcv",
    "DcvNodeport": 31980,
    "DcvDisplayParameterName": "/addf/mlops/dcv-eks-dcv-eks/dcv-display",
    "DcvSocketMountPathParameterName": "/addf/mlops/dcv-eks-dcv-eks/dcv-socket-mount-path"
}
