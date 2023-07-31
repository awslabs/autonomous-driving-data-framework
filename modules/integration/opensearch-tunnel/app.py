import os

import aws_cdk
from aws_cdk import App, CfnOutput

from stack import ProxyStack

account = os.environ["CDK_DEFAULT_ACCOUNT"]
region = os.environ["CDK_DEFAULT_REGION"]

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


vpc_id = os.getenv(_param("VPC_ID"), "")
opensearch_sg_id = os.getenv(_param("OPENSEARCH_SG_ID"), "")
opensearch_domain_endpoint = os.getenv(
    _param("OPENSEARCH_DOMAIN_ENDPOINT"),
    "",
)

port = int(os.getenv(_param("PORT"), "3000"))

project_dir = os.path.dirname(os.path.abspath(__file__))
install_script = os.path.join(project_dir, "install_nginx.sh")


app = App()

stack = ProxyStack(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    env=aws_cdk.Environment(
        account=account,
        region=region,
    ),
    deployment=deployment_name,
    module=module_name,
    vpc_id=vpc_id,
    opensearch_sg_id=opensearch_sg_id,
    opensearch_domain_endpoint=opensearch_domain_endpoint,
    install_script=install_script,
    port=port,
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "OpenSearchProxyInstanceId": stack.instance_id,
            "OpenSearchProxyUrl": stack.dashboard_url,
            "OpenSearchProxyPort": port,
            "SampleSSMCommand": stack.command,
        }
    ),
)


app.synth(force=True)
