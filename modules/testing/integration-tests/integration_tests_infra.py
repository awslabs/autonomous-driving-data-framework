from typing import Any, Dict, List, Optional
import json

import aws_cdk as cdk
import aws_cdk.aws_codebuild as codebuild
import aws_cdk.aws_codepipeline as codepipeline
import aws_cdk.aws_codepipeline_actions as codepipeline_actions
import aws_cdk.aws_codestarnotifications as notifications
import aws_cdk.aws_iam as iam
import aws_cdk.aws_kms as kms
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_deployment as s3_deploy
import aws_cdk.aws_sns as sns
from constructs import Construct


class IntegrationTestsInfrastructure(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        deployment_name: str,
        module_name: str,
        manifests: List[str],
        repo_owner: str,
        repo_name: str,
        oauth_token_secret_name: str,
        seedfarmer_project_name: str,
        branch: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            scope,
            id,
            **kwargs,
        )
        self.prefix = f"{deployment_name}-{module_name}"

        self.artifacts_cmk = kms.Key(
            self,
            "CMK",
            enabled=True,
            enable_key_rotation=True,
            admins=[iam.AccountRootPrincipal()],
            description=f"{self.prefix.capitalize()} Artifacts CMK",
            alias=f"{self.prefix}-artifacts-cmk",
            pending_window=cdk.Duration.days(30),
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )
        self.artifacts_bucket = s3.Bucket(
            self,
            "S3 Integration Testing Artifacts",
            bucket_name=cdk.PhysicalName.GENERATE_IF_NEEDED,
            access_control=s3.BucketAccessControl.BUCKET_OWNER_FULL_CONTROL,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.artifacts_cmk,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            versioned=True,
        )

        s3_deploy.BucketDeployment(
            self,
            "S3ArtifactsDeployment",
            sources=[s3_deploy.Source.asset("artifacts")],
            destination_bucket=self.artifacts_bucket,
            destination_key_prefix="artifacts",
        )
        self.codebuild_service_role = iam.Role(
            self,
            "CodeBuildServiceRole",
            role_name=cdk.PhysicalName.GENERATE_IF_NEEDED,
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            max_session_duration=cdk.Duration.hours(12),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess"),
            ],
        )
        self.artifacts_cmk.grant_encrypt_decrypt(self.codebuild_service_role)

        codebuild.GitHubSourceCredentials(
            self,
            "GitHubCodeBuildCreds",
            access_token=cdk.SecretValue.secrets_manager(oauth_token_secret_name),
        )

        self.pipeline = codepipeline.Pipeline(
            self, "Pipeline", pipeline_name=cdk.PhysicalName.GENERATE_IF_NEEDED
        )

        source_stage = self.pipeline.add_stage(stage_name="Source")
        source_artifact = codepipeline.Artifact()
        source_stage.add_action(
            codepipeline_actions.GitHubSourceAction(
                oauth_token=cdk.SecretValue.secrets_manager(oauth_token_secret_name),
                action_name="Github_Source",
                owner=repo_owner,
                repo=repo_name,
                output=source_artifact,
                branch=branch if branch else "main",
            )
        )

        self.pipeline.add_stage(
            stage_name="SeedFarmerBootstrap",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    action_name="SeedFarmerBootstrap",
                    project=self.create_codebuild_project(
                        "SeedFarmerBootstrap",
                        "artifacts/seedfarmer-bootstrap.yml",
                        "bootstraps seedfarmer",
                        environment_variables={
                            "ARTIFACTS_BUCKET": codebuild.BuildEnvironmentVariable(
                                value=self.artifacts_bucket.bucket_name
                            ),
                            "PRINCIPAL_ROLE": codebuild.BuildEnvironmentVariable(
                                value=self.codebuild_service_role.role_arn
                            ),
                            "SEEDFARMER_PROJECT_NAME": codebuild.BuildEnvironmentVariable(
                                value=f"integ-{seedfarmer_project_name}",
                            ),
                        },
                    ),
                    input=source_artifact,
                    run_order=2,
                ),
            ],
        )

        deploy_project = self.create_codebuild_project(
            "Deploy",
            "artifacts/seedfarmer-deploy.yml",
            f"deploys seedfarmer with manifest(s) {manifests}",
        )
        self.pipeline.add_stage(
            stage_name="Deploy",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    action_name="Deploy",
                    project=deploy_project,
                    environment_variables={
                        "MANIFEST_PATHS": codebuild.BuildEnvironmentVariable(
                            value=json.dumps(manifests)
                        ),
                        "ARTIFACTS_BUCKET": codebuild.BuildEnvironmentVariable(
                            value=self.artifacts_bucket.bucket_name
                        ),
                        "ROLE_ARN": codebuild.BuildEnvironmentVariable(
                            value=self.codebuild_service_role.role_arn
                        ),
                        "SEEDFARMER_PROJECT_NAME": codebuild.BuildEnvironmentVariable(
                            value=f"integ-{seedfarmer_project_name}",
                        ),
                    },
                    input=source_artifact,
                    run_order=3,
                ),
            ],
        )

        self.alerts_topic = sns.Topic(
            self,
            "Slack Alerts Topic",
            topic_name="seedfarmer-integration-tests-slack-alerts",
        )

        rule = notifications.NotificationRule(
            self,
            "Integration Test Status Notification",
            source=self.pipeline,
            events=[
                "codepipeline-pipeline-pipeline-execution-failed",
                "codepipeline-pipeline-pipeline-execution-succeeded",
            ],
            targets=[self.alerts_topic],
        )
        rule.node.add_dependency(self.alerts_topic.node.find_child('Policy'))

    def create_codebuild_project(
        self,
        name: str,
        buildspec_path: str,
        description: Optional[str] = None,
        environment_variables: Optional[Dict[str, Any]] = None,
    ) -> codebuild.PipelineProject:
        return codebuild.PipelineProject(
            self,
            name,
            description=description,
            concurrent_build_limit=1,
            build_spec=codebuild.BuildSpec.from_asset(buildspec_path),
            environment={
                "build_image": codebuild.LinuxBuildImage.AMAZON_LINUX_2_4,
                "compute_type": codebuild.ComputeType.LARGE,
            },
            environment_variables=environment_variables,
            role=self.codebuild_service_role,
            encryption_key=self.artifacts_cmk,
            timeout=cdk.Duration.hours(4),
            badge=False,
        )
