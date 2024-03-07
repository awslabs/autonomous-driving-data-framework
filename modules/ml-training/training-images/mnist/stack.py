# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, cast

import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_iam as iam
from aws_cdk import Duration, Stack, Tags
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class MnistImage(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment_name: str,
        module_name: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            scope,
            id,
            **kwargs,
        )

        Tags.of(scope=cast(IConstruct, self)).add(
            key="Deployment",
            value="aws",
        )

        dep_mod = f"addf-{deployment_name}-{module_name}"

        self.repository_name = dep_mod
        repo = ecr.Repository(self, id=self.repository_name, repository_name=self.repository_name)
        self.image_uri = f"{repo.repository_uri}:mnist"
