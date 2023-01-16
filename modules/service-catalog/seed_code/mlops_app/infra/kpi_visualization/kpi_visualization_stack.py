import os
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Stage,
    aws_s3 as s3,
    aws_glue as glue,
    aws_iam as iam,
    aws_quicksight as quicksight,
    aws_athena as athena,
)
from constructs import Construct


class KpiVisualizationStack(Stack):
    """
    The KPI visualization stack

    Parameters
    ----------
    Stack : Stack
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        env_name: str,
        usecase_name: str,
        crawler_s3_bucket_arn: str,
        crawler_s3_prefix: str,
        quicksight_principal_user_arns: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)
        """
        Parameters
        ----------
        scope : Construct
            The construct's parent
        id : str
            The unique identifier of the resource
        env_name : str
            The name of environment
        source_branch : str
            The name of the branch that will be used as a source
        usecase_name : str
            The name of the use-case
        crawler_s3_bucket_arn : str
            The arn of the bucket for the Glue crawler to crawl
        crawler_s3_prefix : str,
            The folder in the S3 that will be scanned
        quicksight_principal_user_arns : list,
            The list containing arns of the Quicksight principal users
        """

        """
        S3 Bucket
        """
        bucket = s3.Bucket.from_bucket_arn(self, f"{usecase_name}-bucket-{env_name}", crawler_s3_bucket_arn)

        """
        Glue crawler
        """
        crawler_role = iam.Role(
            self,
            f"{usecase_name}-glue-service-role-{env_name}",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            description="Role to access specified S3 bucket from Glue crawler",
            managed_policies=[
                iam.ManagedPolicy.from_managed_policy_arn(
                    self,
                    "managed_policy_glue_service_role",
                    "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole",
                )
            ],
        )

        crawler_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:PutObject"],
                resources=[f"{bucket.bucket_arn}*"],
            )
        )

        crawler_db = glue.CfnDatabase(
            self,
            f"{usecase_name}-crawler-db-{env_name}",
            catalog_id=cdk.Aws.ACCOUNT_ID,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name=f"{usecase_name}-crawler-db-{env_name}",
            ),
        )

        # create crawler with required specifications
        glue.CfnCrawler(
            self,
            f"{usecase_name}-crawler-{env_name}",
            name=f"{usecase_name}-crawler-{env_name}",
            role=crawler_role.role_arn,
            targets=glue.CfnCrawler.TargetsProperty(
                s3_targets=[
                    glue.CfnCrawler.S3TargetProperty(
                        path=bucket.s3_url_for_object(crawler_s3_prefix),
                        exclusions=[
                            "**source-code**",
                            "**data-preparation**",
                            "**debug-output**",
                            "**output**",
                            "**pipelines**",
                            "**profiler-output**",
                            "**rule-output**",
                            "**/*.json",
                            "**/*.sh",
                            "**/*.pkl",
                            "**/*.pkl*",
                            "**/*.gz",
                            "**/*.ts",
                            "**/*.png",
                            "**/*.jpeg",
                            "**/*.jpg",
                            "*.json",
                        ],
                    )
                ],
            ),
            database_name=crawler_db.database_input.name,
            recrawl_policy=glue.CfnCrawler.RecrawlPolicyProperty(recrawl_behavior="CRAWL_NEW_FOLDERS_ONLY"),
            schema_change_policy=glue.CfnCrawler.SchemaChangePolicyProperty(
                delete_behavior="LOG", update_behavior="LOG"
            ),
            schedule=glue.CfnCrawler.ScheduleProperty(schedule_expression="cron(0 8 * * ? *)"),
        )

        """
        Athena Workgroup
        """
        athena_workgroup_name = f"{usecase_name}-kpi-visualization-{env_name}"
        athena_workgroup = athena.CfnWorkGroup(
            self,
            f"{usecase_name}-athena-workgroup-{env_name}",
            name=athena_workgroup_name,
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                publish_cloud_watch_metrics_enabled=True,
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    encryption_configuration=athena.CfnWorkGroup.EncryptionConfigurationProperty(
                        encryption_option="SSE_S3",
                    ),
                    output_location=bucket.s3_url_for_object("athena"),
                ),
            ),
        )

        """
        Quicksight dashboard
        """
        # fetch quicksight service role
        quicksight_role_name = "aws-quicksight-service-role-v0"
        quicksight_service_role = iam.Role.from_role_arn(
            self,
            "quicksight-service-role",
            f"arn:aws:iam::{cdk.Stack.of(self).account}:role/service-role/{quicksight_role_name}",
            mutable=True,
        )
        # grant service role access to the bucket so that Athena can access it
        quicksight_service_role.attach_inline_policy(
            iam.Policy(
                self,
                "athena-s3-access-policy",
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["s3:*"],
                        resources=[f"{bucket.bucket_arn}"],
                    ),
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["s3:GetObject", "s3:PutObject"],
                        resources=[f"{bucket.bucket_arn}/athena/*"],
                    ),
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=["s3:GetObject", "s3:GetObjectVersion"],
                        resources=[f"{bucket.bucket_arn}/{crawler_s3_prefix}/*"],
                    ),
                ],
            )
        )
        if quicksight_principal_user_arns:
            quicksight_datasource_name = f"{usecase_name}-datasource-{env_name}"
            quicksight.CfnDataSource(
                self,
                quicksight_datasource_name,
                data_source_id=quicksight_datasource_name,
                aws_account_id=cdk.Aws.ACCOUNT_ID,
                data_source_parameters=quicksight.CfnDataSource.DataSourceParametersProperty(
                    athena_parameters=quicksight.CfnDataSource.AthenaParametersProperty(
                        work_group=athena_workgroup_name
                    ),
                ),
                name=quicksight_datasource_name,
                permissions=[
                    quicksight.CfnDataSource.ResourcePermissionProperty(
                        actions=[
                            "quicksight:DescribeDataSource",
                            "quicksight:DescribeDataSourcePermissions",
                            "quicksight:PassDataSource",
                            "quicksight:UpdateDataSource",
                            "quicksight:DeleteDataSource",
                            "quicksight:UpdateDataSourcePermissions",
                        ],
                        principal=quicksight_principal_user_arn,
                    )
                    for quicksight_principal_user_arn in quicksight_principal_user_arns
                ],
                ssl_properties=quicksight.CfnDataSource.SslPropertiesProperty(disable_ssl=False),
                type="ATHENA",
            ).add_depends_on(athena_workgroup)
        else:
            print(
                "WARNING: QuickSight Principal User ARNs not defined in `cdk.json` file. Skipping creation of QuickSight DataSource."
            )
