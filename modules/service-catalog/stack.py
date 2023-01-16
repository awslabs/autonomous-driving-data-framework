#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License").
#    You may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import logging
import os
from typing import Any, cast

import aws_cdk.aws_iam as iam
import aws_cdk.aws_s3_assets as assets
import aws_cdk.aws_servicecatalog as servicecatalog
from aws_cdk import Stack, Tags
from constructs import Construct, IConstruct
from service_catalog.products import products

_logger: logging.Logger = logging.getLogger(__name__)


class ServiceCatalogStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment_name: str,
        module_name: str,
        portfolio_access_role_arn: str,
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
        portfolio = servicecatalog.Portfolio(
            self,
            "Portfolio",
            display_name="ADDF_Portfolio",
            provider_name="addf-admin",
            description="Portfolio for application templates provided by ADDF",
            message_language=servicecatalog.MessageLanguage.EN,
        )

        account_root_principle = iam.Role(
            self,
            "AccountRootPrincipal",
            assumed_by=iam.AccountRootPrincipal(),
        )

        portfolio.give_access_to_role(account_root_principle)

        if portfolio_access_role_arn is not None:
            portfolio_access_role = iam.Role.from_role_arn(self, "portfolio-access-role", portfolio_access_role_arn)
            portfolio.give_access_to_role(portfolio_access_role)

        seed_code_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_code")

        for asset_dir in ["mlops_app"]:  # TODO get from file system to dynamically generate assets
            asset_name = "-" + asset_dir.replace("_", "-")
            app_asset = assets.Asset(
                self,
                f"AppAsset{asset_name}",
                path=os.path.join(seed_code_dir, asset_dir),
            )
            product_name = "ApplicationTemplate" + asset_name
            product = servicecatalog.CloudFormationProduct(
                self,
                f"AppTemplateProductRef{asset_name}",
                product_name=product_name,
                owner="addf-admin",
                product_versions=[
                    servicecatalog.CloudFormationProductVersion(
                        cloud_formation_template=servicecatalog.CloudFormationTemplate.from_product_stack(
                            products[asset_dir](self, f"AppTemplateProduct{app_asset}", code_asset=app_asset),
                        ),
                    ),
                ],
            )
            Tags.of(product).add(key="sagemaker:studio-visibility", value="true")

            portfolio.add_product(product)
