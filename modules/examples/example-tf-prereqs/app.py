import os

import aws_cdk
from aws_cdk import App, CfnOutput

from stack import TfPreReqs

# ADDF vars
deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")
hash = os.getenv("ADDF_HASH", "")
tf_s3_backend_encryption_type = os.getenv("ADDF_PARAMETER_S3_ENCRYPTION_TYPE", "SSE")
tf_s3_backend_retention_type = os.getenv("ADDF_PARAMETER_S3_RETENTION_TYPE", "DESTROY")
tf_ddb_retention_type = os.getenv("ADDF_PARAMETER_DDB_RETENTION_TYPE", "DESTROY")

app = App()


stack = TfPreReqs(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    hash=hash,
    tf_s3_backend_encryption_type=tf_s3_backend_encryption_type,
    tf_s3_backend_retention_type=tf_s3_backend_retention_type,
    tf_ddb_retention_type=tf_ddb_retention_type,
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "TfStateBucketName": stack.tf_state_s3bucket.bucket_name,
            "TfLockTable": stack.tf_ddb_lock_table.table_name,
        }
    ),
)


app.synth(force=True)
