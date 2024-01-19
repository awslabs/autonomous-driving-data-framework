# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
from typing import Any, cast

from aws_cdk import Stack, Tags
from aws_cdk import aws_ecr as ecr
from aws_cdk.aws_ecr_assets import DockerImageAsset
from cdk_ecr_deployment import DockerImageName, ECRDeployment
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct


class DcvImagePublishingStack(Stack):  # type: ignore
    def __init__(
        self,
        scope: Construct,
        id: str,
        project_name: str,
        repository_name: str,
        deployment_name: str,
        module_name: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.project_name = project_name
        self.deployment_name = deployment_name
        self.module_name = module_name

        dep_mod = f"{self.project_name}-{self.deployment_name}-{self.module_name}"
        dep_mod = dep_mod[:64]
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=dep_mod)

        repo = ecr.Repository.from_repository_name(self, id=dep_mod + repository_name, repository_name=repository_name)

        local_image = DockerImageAsset(
            self,
            "ImageExtractionDockerImage",
            directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"),
        )

        self.image_uri = f"{repo.repository_uri}:dcv-latest"
        ECRDeployment(
            self,
            "ImageURI",
            src=DockerImageName(local_image.image_uri),
            dest=DockerImageName(self.image_uri),
        )

        NagSuppressions.add_stack_suppressions(
            self,
            apply_to_nested_stacks=True,
            suppressions=[
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-IAM4",
                        "reason": "Managed Policies are for src account roles only",
                    }
                ),
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-IAM5",
                        "reason": "Resource access restriced to resources",
                    }
                ),
            ],
        )
