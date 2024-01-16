# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# type: ignore

import sys
import time

import boto3

emr_client = boto3.client("emr")
emrc_client = boto3.client("emr-containers")
marker = None
prefix = "addf"
deployment_name = sys.argv[1]
module_name = sys.argv[2]


def list_studios():
    """
    List studios
    """
    paginator = emr_client.get_paginator("list_studios")
    studios_list_iterator = paginator.paginate(PaginationConfig={"MaxItems": 10, "StartingToken": marker})
    return studios_list_iterator


def delete_studio(studios_list_iterator):
    """
    Deletes the studios
    """
    for i in studios_list_iterator:
        for studio in i["Studios"]:
            if studio["Name"].startswith(f"{prefix}-{deployment_name}-{module_name[0:14]}"):
                try:
                    emr_client.delete_studio(StudioId=studio["StudioId"])
                    print(f'Deleted the Studio: {studio["StudioId"]}')
                except Exception as ex:
                    print(f'Studio: {studio["StudioId"]} still contains Workspaces. Please delete them')
                    raise ex
        else:
            print("Currently there are no Studios detected")


def list_virtual_clusters():
    """
    Lists Virtual Clusters
    """
    vc_id = None
    vc_list_response = emrc_client.list_virtual_clusters(containerProviderType="EKS", states=["RUNNING"])[
        "virtualClusters"
    ]
    for vc in vc_list_response:
        if vc["name"].startswith(f"{prefix}-{deployment_name}-{module_name[0:14]}"):
            vc_id = vc["id"]
    return vc_id


def delete_managed_endpoints(vc_id):
    """
    Delete Managed endpoints
    """
    response = emrc_client.list_managed_endpoints(virtualClusterId=vc_id, states=["ACTIVE", "TERMINATING"])["endpoints"]
    print(response)
    for mp in response:
        if mp["virtualClusterId"] == vc_id:
            emrc_client.delete_managed_endpoint(id=mp["id"], virtualClusterId=vc_id)
            print(f'Deleted the Managed Endpoint: {mp["id"]}')


def delete_virtual_cluster(vc_id):
    """
    Deletes Virtual Cluster
    """
    emrc_client.delete_virtual_cluster(id=vc_id)
    print(f"Deleted the VirtualCluster: {vc_id}")


if __name__ == "__main__":
    studios_list_iterator = list_studios()
    delete_studio(studios_list_iterator=studios_list_iterator)
    vc_id = list_virtual_clusters()
    if vc_id:
        delete_managed_endpoints(vc_id=vc_id)
        time.sleep(120)
        delete_virtual_cluster(vc_id=vc_id)
    else:
        print("Currently there are no Virtual Clusters detected")
