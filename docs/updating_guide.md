# Autonomous Driving Data Framework (ADDF) Version Updating Guide

Autonomous Driving Data Framework follows the Industry standard `GitOps` model. The project is entirely driven by `Descriptive` prinicples in the form of asking inputs from a module developer via manifest file(s). This guide walks us through the process of updating ADDF version using the latest release of `SeedFarmer 2.0` which helps with `Multi Account and multi region` deployments.

## Steps to update ADDF

### Upgrading an existing single account project deployment created with SeedFarmer v1.x should be possible with the below steps

You will need to fetch the upstream ADDF repository using the below command:

```bash
git fetch upstream
```

You can merge the fetched release branch into your currently working/branch of interest using the below command:

```bash
git merge release/[MAJOR.MINOR.PATCH]
```

#### Create and activate a Virtual environment

```bash
python3 -m venv .venv && source .venv/bin/activate
```

#### Install the requirements

```bash
pip install -r ./requirements.txt
```

#### Modify the Deployment Manifest

- Before you start upgrading, please check the latest format of deployment manifest [here](https://seed-farmer.readthedocs.io/en/latest/manifests.html#deployment-manifest), where you can find out information about the supported attributes
- Add required `toolchainRegion` with the region of your interest
- Add required `targetAccountMappings` with at least one account
  - Mark one account with `default: true` and one region with `default: true`
  - Set the `accountId` under `targetAccountMappings` to the AWS Account you would deploy target modules. You could set the `accountId` as below:

```yaml
targetAccountMappings:
  - alias: primary
    accountId: 1234567890
```

  - Alternatively, you could also set `accountId` as an environment variable inside a `.env` file at the root of the addf project which has the values of global kind of variables using the format `PRIMARY_ACCOUNT=1234567890`. Then, we can set the value of `accountId` to `PRIMARY_ACCOUNT`, which will be dynamically loaded using `pydotenv` library.

```yaml
targetAccountMappings:
  - alias: primary
    accountId:
      valueFrom:
        envVariable: PRIMARY_ACCOUNT
```

- Below is a snippet of how an existing deployment.yaml file would look like

```yaml
name: demo
dockerCredentialsSecret: aws-addf-docker-credentials
groups:
  - name: optionals
    path: manifests/demo/optional-modules.yaml
  - name: core
    path: manifests/demo/core-modules.yaml
  - name: rosbag
    path: manifests/demo/rosbag-modules.yaml
```

- Below is a snippet of how a deployment.yaml file would look like to support the 1.x version of seedfarmer

```yaml
name: demo
toolchainRegion: us-west-2
groups:
  - name: optionals
    path: manifests/example-dev/optional-modules.yaml
  - name: core
    path: manifests/example-dev/core-modules.yaml
  - name: rosbag
    path: manifests/example-dev/rosbag-modules.yaml
targetAccountMappings:
  - alias: primary
    accountId:
      valueFrom:
        envVariable: PRIMARY_ACCOUNT
    default: true
    parametersGlobal:
      dockerCredentialsSecret: aws-addf-docker-credentials
    regionMappings:
      - region: us-west-2
        default: true
```

> The above snippets assume that you are deploying to `us-west-2` region

#### Bootstrapping

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

#### Bootstrap the Seedfarmer

Bootstrap your existing account to convert to a Toolchain and a Target account using the below

```sh
seedfarmer bootstrap toolchain --project addf --trusted-principals [principal-arns] --as-target
```

> `--as-target` sets your account as a target account too

If you want to move from a Single account to a Multi account structure, where you have 1 Tool chain and at least 1 Target account, run the below

```sh
seedfarmer bootstrap toolchain --project addf --trusted-principals [principal-arns]
```

> Before running the above command, set your AWS credentials to the toolchain account

```sh
seedfarmer bootstrap target --project addf --toolchain-account [account_id]
```

> Before running the above command, set your AWS credentials to the Target account

Then, either manually apply or if you have setup a CICD process to handle updates/deployments of ADDF, then you would need to push the changes into your specific remote (user/customer specific remote) maintained for ADDF.

```sh
seedfarmer apply [path_to_manifest] --debug
```

```sh
git add . && git commit -m "upgrade" && git push
```
