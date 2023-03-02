import os
from typing import Any, cast

import aws_cdk.aws_iam as iam
import aws_cdk.aws_s3_assets as assets
import aws_cdk.aws_servicecatalog as servicecatalog
import cdk_nag
from aws_cdk import Aspects, Stack, Tags
from constructs import Construct, IConstruct

from service_catalog.products import products


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

        self.deployment_name = deployment_name
        self.module_name = module_name
        Tags.of(scope=cast(IConstruct, self)).add(
            key="Deployment", value=f"addf-{self.deployment_name}-{self.module_name}"
        )

        self.portfolio = servicecatalog.Portfolio(
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

        self.portfolio.give_access_to_role(account_root_principle)

        if portfolio_access_role_arn is not None:
            self.portfolio_access_role = iam.Role.from_role_arn(
                self, "portfolio-access-role", portfolio_access_role_arn
            )
            self.portfolio.give_access_to_role(self.portfolio_access_role)

        seed_code_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "seed_code"
        )
        for asset_dir_path in next(os.walk(seed_code_dir))[1]:
            asset_dir = os.path.basename(asset_dir_path)
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
                            products[asset_dir](
                                self,
                                f"AppTemplateProduct{app_asset}",
                                code_asset=app_asset,
                            ),
                        ),
                    ),
                ],
            )
            Tags.of(product).add(key="sagemaker:studio-visibility", value="true")

            self.portfolio.add_product(product)

            Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())
