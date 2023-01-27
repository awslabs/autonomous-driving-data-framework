import aws_cdk as cdk
import yaml
from aws_cdk import Aws, Stack, Stage
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import pipelines
from constructs import Construct
from notifications.notifications_stack import NotificationsStack


class PipelineStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        code_repository_name: str,
        sagemaker_project_name: str,
        sagemaker_project_id: str,
        model_package_group_name: str,
        project_short_name: str,
        env_name: str,
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
            artifact_bucket_arn = f"arn:aws:s3:::sagemaker-{Stack.of(self).region}-{Stack.of(self).account}"

        artifact_bucket = s3.Bucket.from_bucket_arn(
            self,
            f"code-pipeline-artifacts-bucket",
            artifact_bucket_arn,
        )

        codepipeline_props = codepipeline.Pipeline(
            self,
            "CodepipelineProperty",
            artifact_bucket=artifact_bucket,
            pipeline_name=f"{project_short_name}-pipeline-{env_name}",
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
            project_short_name=project_short_name,
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
        project_short_name: str,
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
            project_short_name=project_short_name,
            env_name=env_name,
        )
