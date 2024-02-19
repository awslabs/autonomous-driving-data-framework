# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
from typing import Any, List, cast

import aws_cdk as cdk
from aws_cdk import aws_batch as batch
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as aws_lambda
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from constructs import Construct, IConstruct


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
        vpc_id: str,
        private_subnet_ids: List[str],
        emr_job_exec_role_arn: str,
        emr_app_id: str,
        source_bucket_name: str,
        target_bucket_name: str,
        artifacts_bucket_name: str,
        logs_bucket_name: str,
        detection_ddb_name: str,
        on_demand_job_queue_arn: str,
        fargate_job_queue_arn: str,
        parquet_batch_job_def_arn: str,
        png_batch_job_def_arn: str,
        object_detection_image_uri: str,
        object_detection_role_arn: str,
        object_detection_job_concurrency: int,
        object_detection_instance_type: str,
        lane_detection_image_uri: str,
        lane_detection_role_arn: str,
        lane_detection_job_concurrency: int,
        lane_detection_instance_type: str,
        file_suffix: str,
        desired_encoding: str,
        yolo_model: str,
        image_topics: List[str],
        sensor_topics: List[str],
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id, description=stack_description, **kwargs)

        self.project_name = project_name
        self.deployment_name = deployment_name
        self.module_name = module_name

        dep_mod = f"{self.project_name}-{self.deployment_name}-{self.module_name}"
        dep_mod = dep_mod[:64]
        cdk.Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=dep_mod)

        # Sagemaker Security Group
        vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=vpc_id,
        )
        security_group = ec2.SecurityGroup(
            self, "Sagemaker Jobs SG", vpc=vpc, allow_all_outbound=True, description="Sagemaker Processing Jobs SG"
        )

        security_group.add_ingress_rule(peer=security_group, connection=ec2.Port.all_traffic())

        # DynamoDB Tracking Table
        tracking_partition_key = "pk"  # batch_id or drive_id
        tracking_sort_key = "sk"  # batch_id / array_index_id   or drive_id / file_part

        tracking_table = dynamodb.Table(
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

        # DynamoDB Detection Table
        detection_ddb_table = dynamodb.Table.from_table_name(self, "Detection DDB Table", detection_ddb_name)

        # Batch definitions
        on_demand_job_queue = batch.JobQueue.from_job_queue_arn(self, "On Demand Job Queue", on_demand_job_queue_arn)
        fargate_job_queue = batch.JobQueue.from_job_queue_arn(self, "Fargate Job Queue", fargate_job_queue_arn)

        # S3 buckets
        source_bucket = s3.Bucket.from_bucket_name(self, "Source Bucket", source_bucket_name)
        target_bucket = s3.Bucket.from_bucket_name(self, "Target Bucket", target_bucket_name)
        artifacts_bucket = s3.Bucket.from_bucket_name(self, "Artifacts Bucket", artifacts_bucket_name)
        logs_bucket = s3.Bucket.from_bucket_name(self, "Logs Bucket", logs_bucket_name)

        # Define Lambda job for creating a batch of drives
        create_batch_lambda_function = aws_lambda.Function(
            self,
            "CreateBatchOfDrivesFunction",
            code=aws_lambda.Code.from_asset("lambda/create-batch-of-drives/src"),
            handler="lambda_function.lambda_handler",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            environment={
                "DYNAMODB_TABLE": tracking_table.table_name,
                "FILE_SUFFIX": file_suffix,
            },
            timeout=cdk.Duration.minutes(15),
        )
        tracking_table.grant_read_write_data(create_batch_lambda_function)
        source_bucket.grant_read(create_batch_lambda_function)

        # Define step function
        sfn_batch_id = sfn.JsonPath.string_at("$$.Execution.Name")

        create_batch_task = tasks.LambdaInvoke(
            self,
            "Create Batch of Drives",
            lambda_function=create_batch_lambda_function,
            payload=sfn.TaskInput.from_object(
                {
                    "DrivesToProcess": sfn.JsonPath.string_at("$.DrivesToProcess"),
                    "ExecutionID": sfn_batch_id,
                }
            ),
            result_path="$.LambdaOutput",
            result_selector={
                "BatchSize.$": "$.Payload.BatchSize",
            },
        )

        image_extraction_step_machine_task = tasks.BatchSubmitJob(
            self,
            "Image Extraction",
            job_definition_arn=png_batch_job_def_arn,
            job_name="ros-image-pipeline-png",
            job_queue_arn=on_demand_job_queue.job_queue_arn,
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,
            array_size=sfn.JsonPath.number_at("$.LambdaOutput.BatchSize"),
            container_overrides=tasks.BatchContainerOverrides(
                environment={
                    "TABLE_NAME": tracking_table.table_name,
                    "BATCH_ID": sfn_batch_id,
                    "DEBUG": "true",
                    "IMAGE_TOPICS": json.dumps(image_topics),
                    "DESIRED_ENCODING": desired_encoding,
                    "TARGET_BUCKET": target_bucket.bucket_name,
                },
            ),
            result_path=sfn.JsonPath.DISCARD,
        )

        parquet_extraction_step_machine_task = tasks.BatchSubmitJob(
            self,
            "Parquet Extraction",
            job_definition_arn=parquet_batch_job_def_arn,
            job_name="ros-image-pipeline-parquet",
            job_queue_arn=fargate_job_queue.job_queue_arn,
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,
            array_size=sfn.JsonPath.number_at("$.LambdaOutput.BatchSize"),
            container_overrides=tasks.BatchContainerOverrides(
                environment={
                    "TABLE_NAME": tracking_table.table_name,
                    "BATCH_ID": sfn_batch_id,
                    "TOPICS": json.dumps(sensor_topics),
                    "TARGET_BUCKET": target_bucket.bucket_name,
                },
            ),
            result_path=sfn.JsonPath.DISCARD,
        )

        get_image_dirs_task = tasks.CallAwsService(
            self,
            "Get Image Directories",
            service="dynamodb",
            action="query",
            iam_resources=[tracking_table.table_arn],
            parameters={
                "TableName": tracking_table.table_name,
                "KeyConditionExpression": "pk = :pk",
                "ExpressionAttributeValues": {
                    ":pk": {"S": sfn_batch_id},
                },
                "ProjectionExpression": "resized_image_dirs",
            },
            result_path="$.ImageDirs",
            result_selector={
                "S3Paths.$": "$.Items[*].resized_image_dirs.L[*].S",
            },
        )

        object_detection_task = tasks.CallAwsService(
            self,
            "Object Detection",
            service="sagemaker",
            action="createProcessingJob",
            iam_resources=["*"],
            # integration_pattern=sfn.IntegrationPattern.RUN_JOB,  # not supported in CDK (as of 2024-02-08)
            additional_iam_statements=[
                iam.PolicyStatement(
                    actions=["iam:PassRole"],
                    resources=[object_detection_role_arn],
                ),
            ],
            parameters={
                "RoleArn": object_detection_role_arn,
                "ProcessingJobName": sfn.JsonPath.format(
                    "Step-{}-YOLO",
                    sfn.JsonPath.uuid(),
                ),
                "AppSpecification": {
                    "ImageUri": object_detection_image_uri,
                    "ContainerArguments": [
                        "--model",
                        yolo_model,
                    ],
                },
                "NetworkConfig": {
                    "VpcConfig": {
                        "SecurityGroupIds": [security_group.security_group_id],
                        "Subnets": private_subnet_ids,
                    }
                },
                "ProcessingResources": {
                    "ClusterConfig": {
                        "InstanceCount": 1,
                        "InstanceType": object_detection_instance_type,
                        "VolumeSizeInGB": 30,
                    }
                },
                "ProcessingInputs": [
                    {
                        "InputName": "data",
                        "S3Input": {
                            "S3Uri": sfn.JsonPath.format(
                                f"s3://{target_bucket.bucket_name}/{{}}/", sfn.JsonPath.string_at("$")
                            ),
                            "S3DataType": "S3Prefix",
                            "S3InputMode": "File",
                            "S3DataDistributionType": "FullyReplicated",
                            "S3CompressionType": "None",
                            "LocalPath": "/opt/ml/processing/input/",
                        },
                    },
                ],
                "ProcessingOutputConfig": {
                    "Outputs": [
                        {
                            "OutputName": "output",
                            "S3Output": {
                                "S3Uri": sfn.JsonPath.format(
                                    f"s3://{target_bucket.bucket_name}/{{}}_post_obj_dets/", sfn.JsonPath.string_at("$")
                                ),
                                "S3UploadMode": "EndOfJob",
                                "LocalPath": "/opt/ml/processing/output/",
                            },
                        }
                    ]
                },
            },
        )

        sm_local_input = "/opt/ml/processing/input/image"
        sm_local_output = "/opt/ml/processing/output/image"
        sm_local_output_json = "/opt/ml/processing/output/json"
        sm_local_output_csv = "/opt/ml/processing/output/csv"
        lane_detection_task = tasks.CallAwsService(
            self,
            "Lane Detection",
            service="sagemaker",
            action="createProcessingJob",
            iam_resources=["*"],
            # integration_pattern=sfn.IntegrationPattern.RUN_JOB,  # not supported in CDK (as of 2024-02-08)
            additional_iam_statements=[
                iam.PolicyStatement(
                    actions=["iam:PassRole"],
                    resources=[lane_detection_role_arn],
                ),
            ],
            parameters={
                "RoleArn": lane_detection_role_arn,
                "ProcessingJobName": sfn.JsonPath.format(
                    "Step-{}-LANE",
                    sfn.JsonPath.uuid(),
                ),
                "AppSpecification": {
                    "ImageUri": lane_detection_image_uri,
                    "ContainerArguments": [
                        "--save_dir",
                        sm_local_output,
                        "--source",
                        sm_local_input,
                        "--json_path",
                        sm_local_output_json,
                        "--csv_path",
                        sm_local_output_csv,
                    ],
                },
                "NetworkConfig": {
                    "VpcConfig": {
                        "SecurityGroupIds": [security_group.security_group_id],
                        "Subnets": private_subnet_ids,
                    }
                },
                "ProcessingResources": {
                    "ClusterConfig": {
                        "InstanceCount": 1,
                        "InstanceType": lane_detection_instance_type,
                        "VolumeSizeInGB": 30,
                    }
                },
                "ProcessingInputs": [
                    {
                        "InputName": "data",
                        "S3Input": {
                            "S3Uri": sfn.JsonPath.format(
                                f"s3://{target_bucket.bucket_name}/{{}}/", sfn.JsonPath.string_at("$")
                            ),
                            "S3DataType": "S3Prefix",
                            "S3InputMode": "File",
                            "S3DataDistributionType": "FullyReplicated",
                            "S3CompressionType": "None",
                            "LocalPath": sm_local_input,
                        },
                    },
                ],
                "ProcessingOutputConfig": {
                    "Outputs": [
                        {
                            "OutputName": "image_output",
                            "S3Output": {
                                "S3Uri": sfn.JsonPath.format(
                                    f"s3://{target_bucket.bucket_name}/{{}}_post_lane_dets/",
                                    sfn.JsonPath.string_at("$"),
                                ),
                                "S3UploadMode": "EndOfJob",
                                "LocalPath": sm_local_output,
                            },
                        },
                        {
                            "OutputName": "json_output",
                            "S3Output": {
                                "S3Uri": sfn.JsonPath.format(
                                    f"s3://{target_bucket.bucket_name}/{{}}_post_lane_dets/",
                                    sfn.JsonPath.string_at("$"),
                                ),
                                "S3UploadMode": "EndOfJob",
                                "LocalPath": sm_local_output_json,
                            },
                        },
                        {
                            "OutputName": "csv_output",
                            "S3Output": {
                                "S3Uri": sfn.JsonPath.format(
                                    f"s3://{target_bucket.bucket_name}/{{}}_post_lane_dets/",
                                    sfn.JsonPath.string_at("$"),
                                ),
                                "S3UploadMode": "EndOfJob",
                                "LocalPath": sm_local_output_csv,
                            },
                        },
                    ]
                },
            },
        )

        obj_detection_map_task = sfn.Map(
            self,
            "Object Detection Parallel Map",
            items_path="$.ImageDirs.S3Paths",
            max_concurrency=object_detection_job_concurrency,
        ).item_processor(
            self.processing_job_add_wait(
                id=object_detection_task.id,
                start_process_task=object_detection_task,
                wait_time_seconds=15,
            )
        )

        lane_detection_map_task = sfn.Map(
            self,
            "Lane Detection Parallel Map",
            items_path="$.ImageDirs.S3Paths",
            max_concurrency=lane_detection_job_concurrency,
        ).item_processor(
            self.processing_job_add_wait(
                id=lane_detection_task.id,
                start_process_task=lane_detection_task,
                wait_time_seconds=15,
            ),
        )

        emr_task_chain = self.create_emr_task_chain(
            emr_app_id=emr_app_id,
            emr_job_exec_role_arn=emr_job_exec_role_arn,
            target_bucket=target_bucket,
            artifacts_bucket=artifacts_bucket,
            logs_bucket=logs_bucket,
            image_topics=image_topics,
            tracking_table=tracking_table,
            detection_ddb_table=detection_ddb_table,
            batch_id=sfn_batch_id,
        )

        # Define state machine
        definition = (
            create_batch_task.next(
                sfn.Parallel(self, "Sensor Extraction", result_path=sfn.JsonPath.DISCARD)
                .branch(image_extraction_step_machine_task)
                .branch(parquet_extraction_step_machine_task)
            )
            .next(get_image_dirs_task)
            .next(
                sfn.Parallel(self, "Image Labelling", result_path=sfn.JsonPath.DISCARD)
                .branch(obj_detection_map_task)
                .branch(lane_detection_map_task)
            )
            .next(emr_task_chain)
        )

        self.state_machine = sfn.StateMachine(
            self,
            "StateMachine",
            state_machine_name=f"{project_name}-{deployment_name}-rosbag-image-pipeline-{hash}",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
        )

    def processing_job_add_wait(
        self,
        id: str,
        start_process_task: tasks.CallAwsService,
        wait_time_seconds: int,
    ) -> sfn.IChainable:
        start_process_task.add_retry(
            errors=["SageMaker.SageMakerException"],
            interval=cdk.Duration.seconds(5),
            max_attempts=5,
            jitter_strategy=sfn.JitterType.FULL,
        )

        get_job_status_task = tasks.CallAwsService(
            self,
            f"Get {id} Status",
            service="sagemaker",
            action="describeProcessingJob",
            iam_resources=["*"],
            parameters={
                "ProcessingJobName": sfn.JsonPath.array_get_item(
                    sfn.JsonPath.string_split(sfn.JsonPath.string_at("$.ProcessingJobArn"), "/"),
                    1,
                )
            },
            result_path="$.ProcessingJobStatus",
        )

        wait_task = sfn.Wait(
            self,
            f"Wait {id}",
            time=sfn.WaitTime.duration(cdk.Duration.seconds(wait_time_seconds)),
        )

        retry_chain = wait_task.next(get_job_status_task)

        success_state = sfn.Succeed(self, f"{id} Succeeded")
        fail_state = sfn.Fail(self, f"{id} Failed")

        job_status_choice = (
            sfn.Choice(self, f"Did {id} finish?")
            .when(sfn.Condition.string_equals("$.ProcessingJobStatus.ProcessingJobStatus", "Completed"), success_state)
            .when(
                sfn.Condition.or_(
                    sfn.Condition.string_equals("$.ProcessingJobStatus.ProcessingJobStatus", "Failed"),
                    sfn.Condition.string_equals("$.ProcessingJobStatus.ProcessingJobStatus", "Stopped"),
                ),
                fail_state,
            )
            .otherwise(retry_chain)
        )

        return start_process_task.next(get_job_status_task).next(job_status_choice)

    def create_emr_task_chain(
        self,
        emr_app_id: str,
        emr_job_exec_role_arn: str,
        artifacts_bucket: s3.IBucket,
        target_bucket: s3.IBucket,
        logs_bucket: s3.IBucket,
        tracking_table: dynamodb.Table,
        detection_ddb_table: dynamodb.ITable,
        image_topics: List[str],
        batch_id: str,
    ) -> sfn.IChainable:
        emr_app_arn = f"arn:{self.partition}:emr-serverless:{self.region}:{self.account}:/applications/{emr_app_id}"

        s3_emr_job_prefix = "emr-scripts/"
        s3deploy.BucketDeployment(
            self,
            "S3BucketDagDeploymentTestJob",
            sources=[s3deploy.Source.asset(s3_emr_job_prefix)],
            destination_bucket=artifacts_bucket,
            destination_key_prefix=s3_emr_job_prefix,
        )
        s3_script_dir = artifacts_bucket.s3_url_for_object(s3_emr_job_prefix)

        run_job_task = tasks.CallAwsService(
            self,
            "Start Scene Detection Job",
            service="emrserverless",
            action="startJobRun",
            iam_resources=[emr_app_arn],
            iam_action="emr-serverless:startJobRun",
            additional_iam_statements=[
                iam.PolicyStatement(
                    actions=["iam:PassRole"],
                    resources=[emr_job_exec_role_arn],
                ),
            ],
            parameters={
                "ApplicationId": emr_app_id,
                "ExecutionRoleArn": emr_job_exec_role_arn,
                "ClientToken": sfn.JsonPath.uuid(),
                "Name": sfn.JsonPath.format("scene-detection-step-functons-{}", batch_id),
                "JobDriver": {
                    "SparkSubmit": {
                        "EntryPoint": f"{s3_script_dir}detect_scenes.py",
                        "SparkSubmitParameters": f"--jars {s3_script_dir}spark-dynamodb_2.12-1.1.1.jar",
                        "EntryPointArguments": sfn.JsonPath.array(
                            "--batch-metadata-table-name",
                            tracking_table.table_name,
                            "--batch-id",
                            batch_id,
                            "--output-bucket",
                            target_bucket.bucket_name,
                            "--region",
                            self.region,
                            "--output-dynamo-table",
                            detection_ddb_table.table_name,
                            "--image-topics",
                            json.dumps(image_topics),
                        ),
                    },
                },
                "ConfigurationOverrides": {
                    "MonitoringConfiguration": {
                        "ManagedPersistenceMonitoringConfiguration": {
                            "Enabled": True,
                        },
                        "S3MonitoringConfiguration": {
                            "LogUri": logs_bucket.s3_url_for_object("scene-detection"),
                        },
                    },
                },
            },
        )

        get_job_status_task = tasks.CallAwsService(
            self,
            "Get Scene Detection Job Status",
            service="emrserverless",
            action="getJobRun",
            iam_resources=[f"{emr_app_arn}/jobruns/*"],
            iam_action="emr-serverless:getJobRun",
            result_path="$.JobStatus",
            parameters={
                "ApplicationId": sfn.JsonPath.string_at("$.ApplicationId"),
                "JobRunId": sfn.JsonPath.string_at("$.JobRunId"),
            },
        )

        wait_task = sfn.Wait(
            self,
            "Wait for Scene Detection",
            time=sfn.WaitTime.duration(cdk.Duration.seconds(15)),
        )

        retry_chain = wait_task.next(get_job_status_task)

        success_state = sfn.Succeed(self, "Scene Detection Succeeded")
        fail_state = sfn.Fail(self, "Scene Detection Failed")

        job_status_choice = (
            sfn.Choice(self, "Did Scene Detection Finish?")
            .when(sfn.Condition.string_equals("$.JobStatus.JobRun.State", "SUCCESS"), success_state)
            .when(
                sfn.Condition.or_(
                    sfn.Condition.string_equals("$.JobStatus.JobRun.State", "FAILED"),
                    sfn.Condition.string_equals("$.JobStatus.JobRun.State", "CANCELLED"),
                ),
                fail_state,
            )
            .otherwise(retry_chain)
        )

        return run_job_task.next(get_job_status_task).next(job_status_choice)
