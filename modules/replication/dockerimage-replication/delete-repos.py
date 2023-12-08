# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

#!/usr/bin/env python
import boto3
from botocore.exceptions import ClientError, WaiterError

ECR_CLIENT = boto3.client("ecr")
SSM_CLIENT = boto3.client("ssm")


def cleanup_ecr_repos(prefix: str):
    paginator = ECR_CLIENT.get_paginator("describe_repositories")
    for entry in paginator.paginate():
        for repo in entry["repositories"]:
            if repo["repositoryName"].startswith(prefix):
                print("Deleting ECR REPO: {}".format(repo["repositoryName"]))
                try:
                    ECR_CLIENT.delete_repository(repositoryName=repo["repositoryName"], force=True)
                except ClientError as ex:
                    if ex.response["Error"]["Code"] == "RepositoryNotFoundException":
                        print("Repository: {} is not found, no action needed".format(repo["repositoryName"]))
                        continue
                    else:
                        raise ex


def cleanup_ssm_params(path: str):

    paginator = SSM_CLIENT.get_paginator("get_parameters_by_path")

    response_iterator = paginator.paginate(Path=path)

    for page in response_iterator:
        for entry in page["Parameters"]:
            print("Deleting the SSM PARAMETER: {}".format(entry["Name"]))
            try:
                SSM_CLIENT.delete_parameter(Name=entry["Name"])
            except ClientError as ex:
                if ex.response["Error"]["Code"] == "ParameterNotFound":
                    print("SSM PARAMETER: {} is not found, no action needed".format(entry["Name"]))
                    continue
                else:
                    raise ex


# Cleanups ECR Repositories based on a prefix
cleanup_ecr_repos(prefix="idf")

# Cleanups SSM Parameters based on a specific path pattern
# cleanup_ssm_params(path="/idf/eks/chart")
# cleanup_ssm_params(path="/idf/eks/ami")
