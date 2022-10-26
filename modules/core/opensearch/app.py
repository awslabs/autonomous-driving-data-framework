import json
import os

import aws_cdk
from aws_cdk import App, CfnOutput

from stack import OpenSearchStack

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


vpc_id = os.getenv(_param("VPC_ID"))  # required
private_subnet_ids = json.loads(os.getenv("ADDF_PARAMETER_PRIVATE_SUBNET_IDS"))  # type: ignore

if not vpc_id:
    raise Exception("missing input parameter vpc-id")

if not private_subnet_ids:
    raise Exception("missing input parameter private-subnet-ids")

os_data_nodes = int(os.getenv(_param("OPENSEARCH_DATA_NODES"), 1))
os_data_node_instance_type = os.getenv(_param("OPENSEARCH_DATA_NODES_INSTANCE_TYPE"), "r6g.large.search")
os_master_nodes = int(os.getenv(_param("OPENSEARCH_MASTER_NODES"), 0))
os_master_node_instance_type = os.getenv(_param("OPENSEARCH_MASTER_NODES_INSTANCE_TYPE"), "r6g.large.search")
os_ebs_volume_size = int(os.getenv(_param("OPENSEARCH_EBS_VOLUME_SIZE"), 10))

# REF: developerguide/supported-instance-types.html


app = App()

stack = OpenSearchStack(
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
    os_data_nodes=os_data_nodes,
    os_data_node_instance_type=os_data_node_instance_type,
    os_master_nodes=os_master_nodes,
    os_master_node_instance_type=os_master_node_instance_type,
    os_ebs_volume_size=os_ebs_volume_size,
)

CfnOutput(
    scope=stack,
    id="metadata",
    value=stack.to_json_string(
        {
            "OpenSearchDomainEndpoint": stack.domain_endpoint,
            "OpenSearchDashboardUrl": stack.dashboard_url,
            "OpenSearchSecurityGroupId": stack.os_sg_id,
            "OpenSearchDomainName": stack.domain_name,
        }
    ),
)


app.synth(force=True)
