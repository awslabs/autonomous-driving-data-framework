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
from os import path
from os.path import abspath, dirname
from typing import Any, List, Optional, cast

import aws_cdk
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_iam as aws_iam
import aws_cdk.aws_mwaa as aws_mwaa
import aws_cdk.aws_s3 as aws_s3
import aws_cdk.aws_s3_deployment as aws_s3_deployment
import cdk_nag
from aws_cdk import Aspects, Stack, Tags
from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class MWAAStack(Stack):  # type: ignore
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment_name: str,
        module_name: str,
        vpc_id: str,
        private_subnet_ids: List[str],
        dag_bucket_name: Optional[str] = None,
        dag_path: str = "dags",
        environment_class: str = "mw1.small",
        airflow_version: str,
        max_workers: int = 25,
        unique_requirements_file: str,
        **kwargs: Any,
    ) -> None:
        # ADDF Env vars
        self.deployment_name = deployment_name
        self.module_name = module_name

        # CDK Env Vars
        account: str = aws_cdk.Aws.ACCOUNT_ID
        region: str = aws_cdk.Aws.REGION

        super().__init__(scope, id, description="This stack deploys MWAA resources for ADDF", **kwargs)
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{self.deployment_name}")

        self.vpc_id = vpc_id
        self.vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=vpc_id,
        )

        # DAG Bucket
        if dag_bucket_name:
            dag_bucket = aws_s3.Bucket.from_bucket_name(self, "airflow-dag-bucket", dag_bucket_name)
        else:
            dag_bucket = aws_s3.Bucket(
                self,
                id="airflow-dag-bucket",
                bucket_name=f"addf-{self.deployment_name}-{self.module_name}-{account}-{region}",
                removal_policy=aws_cdk.RemovalPolicy.DESTROY,
                encryption=aws_s3.BucketEncryption.KMS_MANAGED,
                block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
                enforce_ssl=True,
            )

        # Upload MWAA files to S3
        plugins_deployment = aws_s3_deployment.BucketDeployment(
            self,
            id="airflow-dag-plugins",
            destination_bucket=dag_bucket,
            sources=[aws_s3_deployment.Source.asset(path.join(dirname(abspath(__file__)), "plugins"))],
            destination_key_prefix="plugins",
        )

        requirements_path = path.join(dirname(abspath(__file__)), "requirements")
        requirements_deployment = aws_s3_deployment.BucketDeployment(
            self,
            id="airflow-dag-requirements",
            destination_bucket=dag_bucket,
            sources=[aws_s3_deployment.Source.asset(requirements_path)],
            destination_key_prefix="requirements",
        )

        # MWAA environment
        # Create MWAA IAM Policies and Roles
        mwaa_policy_document = aws_iam.PolicyDocument(
            statements=[
                aws_iam.PolicyStatement(
                    actions=["airflow:PublishMetrics"],
                    effect=aws_iam.Effect.ALLOW,
                    resources=[f"arn:aws:airflow:{region}:{account}:environment/addf-{deployment_name}-*"],
                ),
                aws_iam.PolicyStatement(
                    actions=["batch:SubmitJob"],
                    effect=aws_iam.Effect.ALLOW,
                    resources=[f"arn:aws:airflow:{region}:{account}:environment/addf-{deployment_name}-*"],
                ),
                aws_iam.PolicyStatement(
                    actions=["eks:DescribeCluster"],
                    effect=aws_iam.Effect.ALLOW,
                    resources=[f"arn:aws:eks:{region}:{account}:cluster/addf-{deployment_name}-*"],
                ),
                aws_iam.PolicyStatement(
                    actions=[
                        "s3:GetBucket*",
                        "s3:GetObject*",
                        "s3:PutObject",
                        "s3:PutObjectAcl",
                        "s3:List*",
                        "s3:PutObjectTagging",
                    ],
                    effect=aws_iam.Effect.ALLOW,
                    resources=[
                        f"{dag_bucket.bucket_arn}/*",
                        f"{dag_bucket.bucket_arn}",
                    ],
                ),
                aws_iam.PolicyStatement(
                    actions=[
                        "kms:Decrypt",
                        "kms:Encrypt",
                        "kms:ReEncrypt*",
                        "kms:DescribeKey",
                        "kms:GenerateDataKey",
                    ],
                    not_resources=[f"arn:aws:kms:*:{account}:key/*"],
                    conditions={"StringLike": {"kms:ViaService": f"sqs.{region}.amazonaws.com"}},
                ),
                aws_iam.PolicyStatement(
                    actions=[
                        "logs:CreateLogStream",
                        "logs:CreateLogGroup",
                        "logs:PutLogEvents",
                        "logs:GetLogEvents",
                        "logs:GetLogRecord",
                        "logs:GetLogGroupFields",
                        "logs:GetQueryResults",
                        "logs:DescribeLogGroups",
                    ],
                    effect=aws_iam.Effect.ALLOW,
                    resources=[f"arn:aws:logs:{region}:{account}:log-group:airflow-addf*"],
                ),
                aws_iam.PolicyStatement(
                    actions=["logs:DescribeLogGroups"],
                    effect=aws_iam.Effect.ALLOW,
                    resources=[f"arn:aws:logs::{account}:*"],
                ),
                aws_iam.PolicyStatement(
                    actions=["cloudwatch:PutMetricData"],
                    effect=aws_iam.Effect.ALLOW,
                    resources=["*"],
                ),
                aws_iam.PolicyStatement(
                    actions=[
                        "sqs:ChangeMessageVisibility",
                        "sqs:DeleteMessage",
                        "sqs:GetQueueAttributes",
                        "sqs:GetQueueUrl",
                        "sqs:ReceiveMessage",
                        "sqs:SendMessage",
                    ],
                    effect=aws_iam.Effect.ALLOW,
                    resources=[f"arn:aws:sqs:{region}:*:airflow-celery-*"],
                ),
                aws_iam.PolicyStatement(
                    actions=["sts:AssumeRole"],
                    effect=aws_iam.Effect.ALLOW,
                    resources=[f"arn:aws:iam::{account}:role/addf-*"],
                ),
                aws_iam.PolicyStatement(
                    actions=["dynamodb:*"],
                    effect=aws_iam.Effect.ALLOW,
                    resources=[
                        f"arn:aws:dynamodb:{self.region}:{self.account}:table/addf-{deployment_name}-{module_name}*"
                    ],
                ),
                aws_iam.PolicyStatement(
                    actions=[
                        "sagemaker:CreateProcessingJob",
                        "sagemaker:DescribeProcessingJob",
                        "sagemaker:ListProcessingJob",
                    ],
                    effect=aws_iam.Effect.ALLOW,
                    resources=[
                        f"arn:aws:sagemaker:{self.region}:{self.account}:processing-job/*",
                    ],
                ),
            ]
        )

        mwaa_service_role = aws_iam.Role(
            self,
            "mwaa-service-role",
            assumed_by=aws_iam.CompositePrincipal(
                aws_iam.ServicePrincipal("airflow.amazonaws.com"),
                aws_iam.ServicePrincipal("airflow-env.amazonaws.com"),
            ),
            inline_policies={"CDKmwaaPolicyDocument": mwaa_policy_document},
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("AWSBatchFullAccess"),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name("AWSXRayDaemonWriteAccess"),
            ],
            path="/service-role/",
        )

        mwaa_service_role.add_to_policy(
            aws_iam.PolicyStatement(
                resources=["*"],
                actions=["iam:PassRole"],
                conditions={"StringEquals": {"iam:PassedToService": "sagemaker.amazonaws.com"}},
            )
        )

        mwaa_logging_conf = aws_mwaa.CfnEnvironment.LoggingConfigurationProperty(
            task_logs=aws_mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(enabled=True, log_level="INFO"),
            worker_logs=aws_mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(enabled=True, log_level="INFO"),
            scheduler_logs=aws_mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(enabled=True, log_level="INFO"),
            dag_processing_logs=aws_mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                enabled=True, log_level="INFO"
            ),
            webserver_logs=aws_mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(enabled=True, log_level="INFO"),
        )

        mwaa_security_group = ec2.SecurityGroup(self, id="mwaa-sg", vpc=self.vpc)
        mwaa_security_group.connections.allow_internally(ec2.Port.all_traffic(), "MWAA")

        mwaa_network_configuration = aws_mwaa.CfnEnvironment.NetworkConfigurationProperty(
            security_group_ids=[mwaa_security_group.security_group_id],
            subnet_ids=private_subnet_ids,
        )

        mwaa_environment = aws_mwaa.CfnEnvironment(
            self,
            id="mwaa-environment",
            dag_s3_path=dag_path,
            airflow_version=airflow_version,
            environment_class=environment_class,
            execution_role_arn=mwaa_service_role.role_arn,
            logging_configuration=mwaa_logging_conf,
            name=f"addf-{self.deployment_name}-{self.module_name}-environment",
            network_configuration=mwaa_network_configuration,
            max_workers=max_workers,
            plugins_s3_path="plugins/plugins.zip",
            requirements_s3_path=f"requirements/{unique_requirements_file}",
            source_bucket_arn=dag_bucket.bucket_arn,
            webserver_access_mode="PUBLIC_ONLY",
        )
        mwaa_environment.node.add_dependency(plugins_deployment)
        mwaa_environment.node.add_dependency(requirements_deployment)

        self.dag_bucket = dag_bucket
        self.dag_path = dag_path
        self.mwaa_environment = mwaa_environment

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks(verbose=True))

        bucket_suppression = [
            {
                "id": "AwsSolutions-S1",
                "reason": "Logs are disabled for demo purposes",
                "applies_to": "*",
            },
            {
                "id": "AwsSolutions-S5",
                "reason": "No OAI needed - no one is accessing this data without explicit permissions",
                "applies_to": "*",
            },
            {
                "id": "AwsSolutions-IAM5",
                "reason": "Resource access restriced to ADDF resources",
                "applies_to": "*",
            },
            {
                "id": "AwsSolutions-IAM4",
                "reason": "Managed Policies are for service account roles only",
                "applies_to": "*",
            },
        ]

        NagSuppressions.add_stack_suppressions(self, bucket_suppression)
