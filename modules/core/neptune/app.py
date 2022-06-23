import json
import os

import aws_cdk
from aws_cdk import App, CfnOutput
from stack import NeptuneStack

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "test")
module_name = os.getenv("ADDF_MODULE_NAME", "core-neptune")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


vpc_id = os.getenv(_param("VPC_ID"))  # required
private_subnet_ids = json.loads(os.getenv("ADDF_PARAMETER_PRIVATE_SUBNET_IDS"))  # required

if not vpc_id:
    raise Exception("missing input parameter vpc-id")

if not private_subnet_ids:
    raise Exception("missing input parameter private-subnet-ids")

num_instances = int(os.getenv(_param("NUMBER_INSTANCES"), "1"))

app = App()

stack = NeptuneStack(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    env=aws_cdk.Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
    deployment=deployment_name,
    module=module_name,
    vpc_id=vpc_id,
    private_subnet_ids=private_subnet_ids,
    number_instances=num_instances,
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "NeptuneClusterId": stack.cluster.cluster_identifier,
            "NeptuneEndpointAddress": stack.cluster.cluster_endpoint.socket_address,
            "NeptuneReadEndpointAddress": stack.cluster.cluster_read_endpoint.socket_address,
            "NeptuneSecurityGroupId": stack.sg_graph_db.security_group_id,
        }
    ),
)


app.synth(force=True)
