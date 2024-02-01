# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any, cast

import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as aws_lambda
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct



def _create_emr_job_run_task_chain(
    scope: Construct,
    id: str,
    emr_job_exec_role: iam.Role,
    emr_app_id: str,
    emr_app_arn: str,    
    job_driver: dict[str, Any],
) -> sfn.IChainable:
    run_job_task = tasks.CallAwsService(
        scope,
        f"{id} Start Job Run",
        service="emrserverless",
        action="startJobRun",
        iam_resources=[emr_app_arn],
        parameters={
            "ApplicationId": emr_app_id,
            "ExecutionRoleArn": emr_job_exec_role.role_arn,
            "JobDriver": job_driver,
            "ClientToken.$": "States.UUID()",
        },
    )

    get_job_status_task = tasks.CallAwsService(
        scope,
        f"{id} Get Job Status",
        service="emrserverless",
        action="getJobRun",
        result_path="$.JobStatus",
        iam_resources=[emr_app_arn],
        parameters={
            "ApplicationId.$": "$.ApplicationId",
            "JobRunId.$": "$.JobRunId",
        },
    )

    job_execution_status_wait = sfn.Wait(
        scope,
        f"{id} Wait Before Checking Job Status",
        time=sfn.WaitTime.duration(cdk.Duration.seconds(30)),
    )

    retry_chain = job_execution_status_wait.next(get_job_status_task)

    success_state = sfn.Succeed(scope, f"{id} Success")
    fail_state = sfn.Fail(scope, f"{id} Fail")

    job_status_choice = sfn.Choice(scope, f"{id} Job Status Choice")\
        .when(sfn.Condition.string_equals("$.JobStatus.JobRun.State", "SUCCESS"), success_state)\
        .when(
            sfn.Condition.or_(
                sfn.Condition.string_equals("$.JobStatus.JobRun.State", "FAILED"),
                sfn.Condition.string_equals("$.JobStatus.JobRun.State", "CANCELLED"),
            ),
            fail_state,
        )\
        .otherwise(retry_chain)
    
    return run_job_task.next(get_job_status_task).next(job_status_choice)


class TemplateStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        project_name: str,
        deployment_name: str,
        module_name: str,
        hash: str,
        stack_description: str,
        emr_job_exec_role_arn: str,
        emr_app_id: str,
        dag_bucket_name: str,
        **kwargs: Any,
    ) -> None:

        super().__init__(scope, id, description=stack_description, **kwargs)

        self.project_name = project_name
        self.deployment_name = deployment_name
        self.module_name = module_name

        dep_mod = f"{self.project_name}-{self.deployment_name}-{self.module_name}"
        dep_mod = dep_mod[:64]
        cdk.Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=dep_mod)

        # DYNAMODB TRACKING TABLE
        tracking_partition_key = "pk"  # batch_id or drive_id
        tracking_sort_key = "sk"  # batch_id / array_index_id   or drive_id / file_part

        table = dynamodb.Table(
            self,
            "Drive Tracking Table",
            table_name=f"{dep_mod}-drive-tracking",
            partition_key=dynamodb.Attribute(name=tracking_partition_key, type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name=tracking_sort_key, type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            point_in_time_recovery=True,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        )


        # Define EMR jobs and step functions
        emr_job_exec_role = iam.Role.from_role_arn(
            self, "EMR Job Execution Role", emr_job_exec_role_arn
        )
        emr_app_arn = f"arn:{self.partition}:emr-serverless:{self.region}:{self.account}:/applications/{emr_app_id}"

        bucket = s3.Bucket.from_bucket_name(
            self, "DAG Bucket", dag_bucket_name
        )

        s3_emr_job_prefix = "emr-job-definitions/"
        s3deploy.BucketDeployment(
            self,
            "S3BucketDagDeploymentTestJob",
            sources=[s3deploy.Source.asset("emr-scripts/")],
            destination_bucket=bucket,
            destination_key_prefix=s3_emr_job_prefix,
        )

        emr_job_run = _create_emr_job_run_task_chain(
            self,
            "Create Batch of Drives",
            emr_job_exec_role=emr_job_exec_role,
            emr_app_id=emr_app_id,
            emr_app_arn=emr_app_arn,
            job_driver={
                "SparkSubmit": {
                    "EntryPoint": bucket.s3_url_for_object(f"{s3_emr_job_prefix}create-batch-of-drives.py"),
                    "EntryPointArguments": [bucket.s3_url_for_object("emr-serverless-spark/output")],
                    "SparkSubmitParameters": (
                        "--conf spark.executor.cores=1 "
                        "--conf spark.executor.memory=4g "
                        "--conf spark.driver.cores=1 "
                        "--conf spark.driver.memory=4g "
                        "--conf spark.executor.instances=1"
                    ),
                },
            }
        )

        definition = emr_job_run

        state_machine = sfn.StateMachine(
            self,
            "StateMachine",
            state_machine_name=f"{project_name}-{deployment_name}-rosbag-image-pipeline-{hash}",
            definition=definition,
        )

        state_machine.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "emr-serverless:StartJobRun",
                    "emr-serverless:GetJobRun",
                    "emr-serverless:CancelJobRun",
                ],
                resources=[
                    emr_app_arn,
                    f"{emr_app_arn}/jobruns/*",
                ],
            )
        )
        emr_job_exec_role.grant_pass_role(state_machine)

        NagSuppressions.add_stack_suppressions(
            self,
            apply_to_nested_stacks=True,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Managed Policies are for service account roles only",
                ),
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Resource access restriced to resources",
                ),
            ],
        )
