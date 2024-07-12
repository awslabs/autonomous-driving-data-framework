import os
from typing import Any, Dict

import boto3  # type: ignore

eks = boto3.client("eks")
as_client = boto3.client("autoscaling")

# This script fixes missing tags for the cluster autoscaler that need to be added to the nodegroup autoscaling group
# docs:
# https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/cloudprovider/aws/README.md#auto-discovery-setup
# issue: https://github.com/aws/aws-cdk/issues/29280
# container-roadmap: https://github.com/aws/containers-roadmap/issues/1541

CLUSTER_NAME = os.environ["SEEDFARMER_PARAMETER_EKS_CLUSTER_NAME"]
LABEL_TAG_PREFIX = "k8s.io/cluster-autoscaler/node-template/label"

nodegroup_names = eks.list_nodegroups(clusterName=CLUSTER_NAME)["nodegroups"]


def get_asg_tag(asg_name: str, key: str, value: str) -> Dict[str, Any]:
    return {
        "ResourceId": asg_name,
        "ResourceType": "auto-scaling-group",
        "Key": key,
        "Value": value,
        "PropagateAtLaunch": True,
    }


for nodegroup_name in nodegroup_names:
    print(f"Node Group: {nodegroup_name}")

    nodegroup = eks.describe_nodegroup(
        clusterName=CLUSTER_NAME, nodegroupName=nodegroup_name
    )["nodegroup"]
    labels = nodegroup["labels"]

    if labels:
        print(
            f"""Found autoscaling group for NodeGroup ({nodegroup_name}) with eks_node_labels ({labels}).
            Checking if any cluster-autoscaler tags are missing..."""
        )
        asg_name = nodegroup["resources"]["autoScalingGroups"][0]["name"]

        asg = as_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])[
            "AutoScalingGroups"
        ][0]

        tags = asg["Tags"]
        print("Tags:")
        for tag in tags:
            print(f"{tag['Key']}: {tag['Value']}")
        tag_keys = [tag["Key"] for tag in tags]

        target_tags = []

        for label in labels.keys():
            cluster_autoscaler_label_tag = f"{LABEL_TAG_PREFIX}/{label}"
            if cluster_autoscaler_label_tag not in tag_keys:
                target_tags.append(
                    get_asg_tag(asg_name, cluster_autoscaler_label_tag, labels[label])
                )

        if target_tags:
            print(f"Tags to update: {target_tags}")
            create_update_tags_response = as_client.create_or_update_tags(
                Tags=target_tags
            )
            if (
                create_update_tags_response
                and create_update_tags_response["ResponseMetadata"]["HTTPStatusCode"]
                == 200
            ):
                print("Tags updated")
            else:
                print(f"Error: {create_update_tags_response}")
        else:
            print(
                f"All cluster-autoscaler tags exist on Node Group ({nodegroup_name}) ASG({asg_name}). Doing nothing..."
            )
