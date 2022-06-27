# Autonomous Driving Data Framework (ADDF) Deployment Guide

Autonomous Driving Data Framework follows the Industry standard `GitOps` model. The project is entirely driven by `Descriptive` prinicples in the form of asking inputs from a module developer via manifest file(s).

## Steps to deploy ADDF

### Clone the project

You will need to clone the ADDF repository and checkout a release branch using the below command:

```bash
git clone --origin upstream --branch release/0.1.0 https://github.com/awslabs/autonomouse-driving-data-framework
```

> The release version can be replaced with the version of interest

You should move into the ADDF repository:

```bash
cd autonomouse-driving-data-framework
```

#### Create and activate a Virtual environment

```bash
python3 -m venv .venv && source .venv/bin/activate
```

#### Install the requirements

```bash
pip install -r ./requirements.txt
```

#### Setting the AWS Region

ADDF submits build information to AWS CodeBuild via AWS CodeSeeder.  The initial submittal is done via AWS CLI, leveraging the configured active AWS profile.  If you would like to deploy ADDF to a region other than the region configured for the profile, you can explicitly set the region via:

```bash
export AWS_DEFAULT_REGION=<region-name>   (ex. us-east-1, eu-central-1)
```

Please see [HERE for details](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html)

#### Bootstrap the CDKV2

We use AWS CDK V2 as the standard CDK version because CDK V1 is set to maintenance mode beginning June 1, 2022. You  would need to bootstrap the CDK environment (one time per region) with V2 - see [HERE](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html).

```bash
cdk bootstrap aws://<account>/<region>
```

#### Prepare the Manifests for Deployment

Create a copy of your target manifests directory using the below command, where you will locate sample manifests in the name of `example-dev` and `example-prod`. You should create a directory with your desired deployment names like `uat`, `demo`. Below example uses `demo` as the deployment name

```bash
cp -R manifests/example-dev manifests/demo
sed -i .bak "s/example-dev/demo/g" manifests/demo/deployment.yaml
```
If running in a Cloud9 instance, this the command for a `sed` replace:
```bash
cp -R manifests/example-dev manifests/demo
sed -i "s/example-dev/demo/g" manifests/demo/deployment.yaml
```

#### Prepare the AWS SecretsManager

As part of this example `demo` deployment, there are modules that leverage credentials for access. We store these credentials in AWS SecretsManager. We have provided a bash script to populate AWS SecretsManager with default values for those modules that need them located in `scripts/setup-secrets-example.sh`.  
Run the bash script from commandline with the following:

> Below script uses `jq`.  Please install it via [these instructions](https://stedolan.github.io/jq/download/)

```bash
source scripts/setup-secrets-example.sh
```

### Deployment WalkThrough

For the below walkthrough, let us use the `manifests/demo/` directory for deployment, where the deploymemt name is set to `demo`.

File `deployment.yaml` is the top level manifest, which should include the modules you wanted to deploy, grouped under logical containers called `group`.  Please see [manifests](https://seed-farmer.readthedocs.io/en/latest/manifests.html) for more details.

> Note:
> All paths inside the manifest files should be relative to the root of the project. For ex: if you want to include a module manifest `demo-modules.yaml` in your deplopyment.yaml, you should include the manifest in the path as `manifests/demo/demo-modules.yaml` and declare the path as `manifests/demo/demo-modules.yaml` in the deployment.yaml file.

#### Dockerhub Support

To avoid throttling from `DockerHub` when building images, you should create a parameter/re-use an existing parameter in `AWS Secrets Manager` to store your DockerHub username and password.  NOTE: This is optional, but you may experience throttling at DockerHub.  To create an account, see [DockerHub](https://hub.docker.com/signup).

To create/update the default secret (aws-addf-docker-credentials) run:

```bash
./scripts/setup-secrets-dockerhub.sh
```

> Note:
> For additional info on setting up the secret manually see [manifests](https://seed-farmer.readthedocs.io/en/latest/manifests.html#deployment-manifest) guide for details.
> The `demo` modules leverages DockerHub, so you should populate the SecretsManager as indicated in [manifests](https://seed-farmer.readthedocs.io/en/latest/manifests.html#deployment-manifest).

For the walkthrough, we have few manifests declared within `demo` directory which installs the following modules in sequence. If you do not wish to know what modules the demo deployment is doing, you can skip reading this section:

  * `Group` name is set to `optionals` to install the following, sourcing from the manifest `manifests/demo/optional-modules.yaml`:
    * Creates a `networking` module (creates vpc, 2 Public/Private subnets, IGW, NAT, Gateway endpoints etc)
    * Creates a `datalake-buckets` module (creates shared buckets for datalake, logging and artifacts etc)
  * `Group` name is set to `core` to install the following, sourcing from the manifest `manifests/demo/core-modules.yaml`:
    * Creates `eks` module (creates AWS EKS Compute environment with standard plugins installed)
    * Creates `mwaa` module(creates AWS Managed Airflow cluster for orchestration of dags)
    * Creates `metadata-storgae` module(creates shared AWS DynamoDB and AWS Glue databases)
    * Creates `opensearch` module (creates AWS Managed Opensearch for ingesting app/infra logs)
  * `Group` name is set to `examples` to install the following, sourcing from the manifest `manifests/demo/example-modules.yaml`:
    * Creates `example-dags` module (Demos an example on how to deploy dags from target modules using the shared mwaa module)
  * `Group` name is set to `rosbag` to install the following, sourcing from the manifest `manifests/demo/rosbag-modules.yaml`:
    * Creates `rosbag-scene-detection` module
    * Creates `rosbag-webviz` module
  * `Group` name is set to `simulations` to install the following, sourcing from the manifest `manifests/demo/simulation-modules.yaml`:
    * Creates `k8s-managed-simulations` module which deploys different types of Kubernetes driven simulations
    * Creates `batch-managed` module which deploys AWS Batch Compute environment and helps launching Batch Jobs
  * `Group` name is set to `integration` to install the following, sourcing from the manifest `manifests/demo/integration-modules.yaml`:
    * Creates `eks-os` module which integrates EKS Cluster with OpenSearch
    * Creates `opensearch-proxy` module which creates a Proxy to  OpenSearch Cluster
    * Creates `rosbag-ddb-to-os` module which integrates DynamoDB table from Rosbag module with OpenSearch
    * Creates `emrlogs-to-os` module which integrates EMR Cluster's logs to OpenSearch
  * `Group` name is set to `ide` to install the following, sourcing from the manifest `manifests/demo/integration-modules.yaml`:
    * Creates `jupyter-hub` module
    * Creates `vscode` module

#### Deploy

Below is the command to deploy the modules using the `SeedFarmer` CLI using the main manifest `deployment.yaml`:

```bash
seedfarmer apply manifests/demo/deployment.yaml
```

#### Destroy

Below is the command to destroy all the modules related to a deployment:

```bash
seedfarmer destroy <<DEPLOYMENT_NAME>>
```

> Note:
> Replace the `DEPLOYMENT_NAME` with the desired deployment name of your environment. For ex: `demo`
> You can pass an optional `--debug` flag to the above command for getting debug level output

### FAQS
