import aws_cdk.aws_codecommit as codecommit
import aws_cdk.aws_servicecatalog as servicecatalog
from aws_cdk import CfnOutput, CfnParameter


class MLopsAppTemplateProduct(servicecatalog.ProductStack):
    def __init__(self, scope, id, code_asset):
        super().__init__(scope, id)

        sagemaker_project_name = CfnParameter(
            self,
            "SageMakerProjectName",
            type="String",
            description="Name of the project.",
        )
        sagemaker_project_id = CfnParameter(
            self,
            "SageMakerProjectId",
            type="String",
            description="Service generated Id of the project.",
        )
        prefix = f"{sagemaker_project_name.value_as_string}-{sagemaker_project_id.value_as_string}"
        CfnOutput(
            self,
            "AssetPath",
            value=code_asset.asset_path,
        )
        CfnOutput(
            self,
            "AssetBucket",
            value=code_asset.bucket.bucket_arn,
        )

        codecommit.Repository(
            self,
            id="Repo",
            repository_name=f"{prefix}-repository",
            code=codecommit.Code.from_asset(code_asset),
        )


# key should be the same as asset_dir, i.e.
# mlops_app corresponds to modules/service-catalog/seed_code/mlops_app
products = {"mlops_app": MLopsAppTemplateProduct}
