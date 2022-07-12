import json
import os
import shutil

import aws_cdk
from aws_cdk import App, CfnOutput
from stack import MWAAStack

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME")
module_name = os.getenv("ADDF_MODULE_NAME")
vpc_id = os.getenv("ADDF_PARAMETER_VPC_ID")
private_subnet_ids = json.loads(os.getenv("ADDF_PARAMETER_PRIVATE_SUBNET_IDS"))  # type: ignore
dag_bucket_name = os.getenv("ADDF_PARAMETER_DAG_BUCKET_NAME")
airflow_version = os.getenv("ADDF_PARAMETER_AIRFLOW_VERSION")
dag_path = os.getenv("ADDF_PARAMETER_DAG_PATH")
environment_class = os.getenv("ADDF_PARAMETER_ENVIRONMENT_CLASS")
max_workers = os.getenv("ADDF_PARAMETER_MAX_WORKERS", "1")
unique_requirements_file = os.getenv("UNIQUE_REQUIREMENTS_FILE")

if not vpc_id:
    raise Exception("missing input parameter vpc-id")

if not private_subnet_ids:
    raise Exception("missing input parameter private-subnet-ids")

app = App()

# zip plugin
shutil.make_archive("plugins/plugins", "zip", "plugins/")

optional_args = {}
if dag_bucket_name:
    optional_args["dag_bucket_name"] = dag_bucket_name
if dag_path:
    optional_args["dag_path"] = dag_path
if environment_class:
    optional_args["environment_class"] = environment_class
if max_workers and max_workers.isnumeric():
    optional_args["max_workers"] = int(max_workers)  # type: ignore
optional_args["airflow_version"] = airflow_version if airflow_version else "2.2.2"


stack = MWAAStack(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,  # type: ignore
    module_name=module_name,  # type: ignore
    vpc_id=vpc_id,
    private_subnet_ids=private_subnet_ids,
    unique_requirements_file=unique_requirements_file,  # type: ignore
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
    **optional_args,  # type: ignore
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "DagBucketName": stack.dag_bucket.bucket_name,
            "DagPath": stack.dag_path,
            "MwaaExecRoleArn": stack.mwaa_environment.execution_role_arn,
        }
    ),
)

app.synth(force=True)
