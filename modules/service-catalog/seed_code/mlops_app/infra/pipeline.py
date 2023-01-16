import os

import aws_cdk as cdk
from aws_cdk import (
    Aws,
    Stack,
    Stage,
    aws_codebuild as codebuild,
    aws_codecommit as codecommit,
    aws_codepipeline as codepipeline,
    aws_iam as iam,
    aws_s3 as s3,
    pipelines,
)
from constructs import Construct
from kpi_visualization.kpi_visualization_stack import KpiVisualizationStack
from notifications.notifications_stack import NotificationsStack
import yaml

env_name = "stable"


class PipelineStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        code_repository_name: str,
        sagemaker_project_name: str,
        sagemaker_project_id: str,
        model_package_group_name: str,
        usecase_name: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)
        source = pipelines.CodePipelineSource.code_commit(
            repository=codecommit.Repository.from_repository_name(
                self,
                f"source-repo-{sagemaker_project_name}-{sagemaker_project_id}",
                repository_name=code_repository_name,
            ),
            branch="main",
        )
        code_build_role = iam.Role(
            self,
            f"codebuild-{sagemaker_project_name}-{sagemaker_project_id}",
            role_name=f"CodeBuildRole-{sagemaker_project_name}",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("PowerUserAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("IAMFullAccess"),
            ],
        )
        # TODO narrow down
        sm_role = iam.Role(
            self,
            f"sm-role-{sagemaker_project_name}-{sagemaker_project_id}",
            role_name=f"sm-role-{sagemaker_project_name}-{sagemaker_project_id}",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
            ],
        )
        artifact_bucket_arn = self.node.try_get_context("artifact_bucket_arn")

        # use default value for s3 bucket if not provided through 'cdk.json' file
        if not artifact_bucket_arn:
            artifact_bucket_arn = (
                f"arn:aws:s3:::addf-shared-infra-artifacts-bucket-{Stack.of(self).region}-{Stack.of(self).account}"
            )

        artifact_bucket = s3.Bucket.from_bucket_arn(
            self,
            f"code-pipeline-artifacts-bucket",
            artifact_bucket_arn,
        )

        codepipeline_props = codepipeline.Pipeline(
            self,
            "CodepipelineProperty",
            artifact_bucket=artifact_bucket,
            pipeline_name=f"{usecase_name}-pipeline-{env_name}",
        )

        self.pipeline = pipelines.CodePipeline(
            self,
            f"{sagemaker_project_name}-{sagemaker_project_id}-pipeline",
            code_pipeline=codepipeline_props,
            publish_assets_in_parallel=False,
            self_mutation=True,
            synth=pipelines.CodeBuildStep(
                "Synth",
                input=source,
                build_environment=codebuild.BuildEnvironment(
                    build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                    privileged=False,
                ),
                commands=[
                    "cd infra",
                    "pip install -r requirements.txt",
                    "npm install -g aws-cdk",
                    'cdk synth --app "python app.py"',
                ],
                role=code_build_role,
                primary_output_directory="infra/cdk.out",
            ),
        )
        notification_stage_construct = NotificationStage(
            self,
            f"{sagemaker_project_name}-{sagemaker_project_id}-notifications-stage",
            sagemaker_project_name,
            sagemaker_project_id,
            model_package_group_name,
            usecase_name=usecase_name,
            env_name=env_name,
        )
        notification_stage = self.pipeline.add_stage(notification_stage_construct)

        sm_pipelines_buildspec = self.convert_yaml_to_json("../buildspec.yaml")
        notification_stage.add_post(
            pipelines.CodeBuildStep(
                f"SageMakerPipeline.Upsert",
                input=source,
                commands=[],
                build_environment=codebuild.BuildEnvironment(
                    build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                    environment_variables={
                        "SAGEMAKER_PROJECT_NAME": codebuild.BuildEnvironmentVariable(
                            value=sagemaker_project_name,
                        ),
                        "SAGEMAKER_PROJECT_ID": codebuild.BuildEnvironmentVariable(
                            value=sagemaker_project_id,
                        ),
                        "SAGEMAKER_PIPELINE_ROLE_ARN": codebuild.BuildEnvironmentVariable(
                            value=sm_role.role_arn,
                        ),
                        "AWS_REGION": codebuild.BuildEnvironmentVariable(
                            value=Aws.REGION,
                        ),
                    },
                ),
                partial_build_spec=codebuild.BuildSpec.from_object(
                    sm_pipelines_buildspec,
                ),
                role=code_build_role,
            ),
        )

        crawler_s3_bucket_arn = self.node.try_get_context("crawler_s3_bucket_arn")

        # use default value for s3 bucket if not provided through 'cdk.json' file
        if not crawler_s3_bucket_arn:
            crawler_s3_bucket_arn = f"arn:aws:s3:::sagemaker-{Stack.of(self).region}-{Stack.of(self).account}"

        self.pipeline.add_stage(
            KpiVisualizationStage(
                self,
                f"{usecase_name}-kpi-visualization-stack-{env_name}",
                env_name=env_name,
                usecase_name=usecase_name,
                crawler_s3_bucket_arn=crawler_s3_bucket_arn,
            ),
        )

        artifact_bucket.grant_read_write(code_build_role)

    def convert_yaml_to_json(self, file_name):
        with open(file_name, "r") as buildspec_yaml:
            return yaml.safe_load(buildspec_yaml)


class NotificationStage(Stage):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        sagemaker_project_name: str,
        sagemaker_project_id: str,
        model_package_group_name: str,
        usecase_name: str,
        env_name: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)
        self.notification_stack = NotificationsStack(
            self,
            f"{sagemaker_project_name}-{sagemaker_project_id}-notif-stack",
            sagemaker_project_name=sagemaker_project_name,
            sagemaker_project_id=sagemaker_project_id,
            model_package_group_name=model_package_group_name,
            usecase_name=usecase_name,
            env_name=env_name,
        )


class KpiVisualizationStage(Stage):
    """
    Creates the KPI visualization stage for your CDK pipeline

    Parameters
    ----------
    Stage : Stage
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        env_name: str,
        usecase_name: str,
        crawler_s3_bucket_arn: str,
        **kwargs,
    ):
        """
        Parameters
        ----------
        scope : Construct
            The construct's parent
        id : str
            The unique identifier of the resource
        env_name : str
            The name of environment
        """
        super().__init__(scope, id, **kwargs)

        quicksight_principal_user_arns = self.node.try_get_context("quicksight_principal_user_arns")

        crawler_s3_prefix = f"use-case={usecase_name}"

        environment = cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        )

        KpiVisualizationStack(
            self,
            f"{usecase_name}-kpi-visualization-stack-{env_name}",
            env_name=env_name,
            usecase_name=usecase_name,
            crawler_s3_bucket_arn=crawler_s3_bucket_arn,
            crawler_s3_prefix=crawler_s3_prefix,
            quicksight_principal_user_arns=quicksight_principal_user_arns,
            env=environment,
        )
