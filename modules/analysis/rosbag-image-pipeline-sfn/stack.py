# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict, cast

import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_iam as iam
import aws_cdk.aws_stepfunctions as sfn
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_stepfunctions_tasks as tasks
import cdk_nag
from aws_cdk import Aspects, Duration, RemovalPolicy, Stack, Tags
from aws_cdk import aws_dynamodb as dynamo
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class AwsBatchPipeline(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment_name: str,
        module_name: str,
        target_bucket_name: str,
        vpc_id: str,
        bucket_access_policy: str,
        job_queues: Dict[str, str],
        job_definitions: Dict[str, str],
        object_detection_config: Dict[str, str],
        lane_detection_config: Dict[str, str],
        emr_job_config: Dict[str, str],
        stack_description: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            scope,
            id,
            description=stack_description,
            **kwargs,
        )

        self.deployment_name = deployment_name
        self.module_name = module_name
        self.bucket_access_policy = bucket_access_policy
        self.vpc_id = vpc_id
        self.job_queues = job_queues
        self.job_definitions = job_definitions
        self.target_bucket = s3.Bucket.from_bucket_name(target_bucket_name)
        self.object_detection_config = object_detection_config
        self.lane_detection_config = lane_detection_config
        self.emr_job_config = emr_job_config

        Tags.of(scope=cast(IConstruct, self)).add(
            key="Deployment",
            value="aws",
        )

        dep_mod = f"addf-{self.deployment_name}-{self.module_name}"

        # Private Subnets & SG
        vpc = ec2.Vpc.from_lookup(self, vpc_id=self.vpc_id)
        self.private_subnet_ids = vpc.private_subnet_ids
        self.security_group_id = vpc.security_group_id

        # DYNAMODB TRACKING TABLE
        self.tracking_table_name = f"{dep_mod}-drive-tracking"
        tracking_partition_key = "pk"  # batch_id or drive_id
        tracking_sort_key = "sk"  # batch_id / array_index_id   or drive_id / file_part

        self.tracking_table = dynamo.Table(
            self,
            self.tracking_table_name,
            table_name=self.tracking_table_name,
            partition_key=dynamo.Attribute(name=tracking_partition_key, type=dynamo.AttributeType.STRING),
            sort_key=dynamo.Attribute(name=tracking_sort_key, type=dynamo.AttributeType.STRING),
            billing_mode=dynamo.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True,
            stream=dynamo.StreamViewType.NEW_AND_OLD_IMAGES,
        )

        # Create Dag IAM Role and policy
        policy_statements = [
            iam.PolicyStatement(
                actions=["ecr:*"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:ecr:{self.region}:{self.account}:repository/{dep_mod}*"],
            ),
            iam.PolicyStatement(
                actions=[
                    "batch:UntagResource",
                    "batch:DeregisterJobDefinition",
                    "batch:TerminateJob",
                    "batch:CancelJob",
                    "batch:SubmitJob",
                    "batch:RegisterJobDefinition",
                    "batch:TagResource",
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    *job_queues.values(),
                    *job_definitions.values(),
                    f"arn:aws:batch:{self.region}:{self.account}:job/*",
                ],
            ),
            iam.PolicyStatement(
                actions=[
                    "iam:PassRole",
                ],
                effect=iam.Effect.ALLOW,
                resources=[lane_detection_config["LaneDetectionRole"], object_detection_config["ObjectDetectionRole"]],
            ),
            iam.PolicyStatement(
                actions=[
                    "batch:Describe*",
                    "batch:List*",
                ],
                effect=iam.Effect.ALLOW,
                resources=[
                    "*",
                ],
            ),
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:GetObjectAcl", "s3:ListBucket"],
                effect=iam.Effect.ALLOW,
                resources=["arn:aws:s3:::addf-*", "arn:aws:s3:::addf-*/*"],
            ),
        ]
        dag_document = iam.PolicyDocument(statements=policy_statements)

        dag_role_name = f"{dep_mod}-dag-{self.region}"

        self.dag_role = iam.Role(
            self,
            f"dag-role-{dep_mod}",
            assumed_by=iam.CompositePrincipal(
                iam.ArnPrincipal(self.mwaa_exec_role),
            ),
            inline_policies={"DagPolicyDocument": dag_document},
            managed_policies=[
                iam.ManagedPolicy.from_managed_policy_arn(
                    self, id="fullaccess", managed_policy_arn=self.bucket_access_policy
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
            ],
            role_name=dag_role_name,
            max_session_duration=Duration.hours(12),
            path="/",
        )

        dynamo_query = tasks.CallAwsService(
            self,
            service="dynamodb",
            action="query",
            parameters={
                "TableName": self.tracking_table.table_name,
                "KeyConditionExpression": "pk = :pk",
                "ExpressionAttributeValues": "':pk': S.$: $.executionContext.execName",
            },
            iam_resources=[self.tracking_table.table_arn],
            result_path="$.ddbCount",
        )
        map_each_driver = sfn.CustomState(
            self,
            "Map Each Driver",
            state_json={
                "Map Each Driver": {
                    "Type": "Map",
                    "ItemProcessor": {
                        "ProcessorConfig": {"Mode": "INLINE"},
                        "StartAt": "For Each S3 Key in Path",
                        "States": {
                            "For Each S3 Key in Path": {
                                "Type": "Map",
                                "ItemProcessor": {
                                    "ProcessorConfig": {"Mode": "DISTRIBUTED", "ExecutionType": "STANDARD"},
                                    "StartAt": "BatchWriteItem",
                                    "States": {
                                        "BatchWriteItem": {
                                            "Type": "Task",
                                            "Resource": "arn:aws:states:::dynamodb:putItem",
                                            "Parameters": {
                                                "TableName": "addf-aws-solutions-analysis-rip-drive-tracking",
                                                "Item": {
                                                    "pk": {"S.$": "$.execName"},
                                                    "sk": {"S.$": "$.index"},
                                                    "drive_id": {"S.$": "$.drive"},
                                                    "file_id": {
                                                        "S.$": "States.ArrayGetItem(States.StringSplit($.Key.Key, '/'), States.MathAdd(States.ArrayLength(States.StringSplit($.Key.Key, '/')), -1))"
                                                    },
                                                    "s3_bucket": {"S.$": "$.bucket"},
                                                    "s3_key": {"S.$": "$.Key.Key"},
                                                },
                                            },
                                            "End": True,
                                        }
                                    },
                                },
                                "Label": "ForEachS3KeyinPath",
                                "MaxConcurrency": 1000,
                                "ItemReader": {
                                    "Resource": "arn:aws:states:::s3:listObjectsV2",
                                    "Parameters": {"Bucket.$": "$.s3.bucket", "Prefix.$": "$.s3.prefix"},
                                },
                                "End": True,
                                "ItemSelector": {
                                    "drive.$": "$.s3.drive",
                                    "bucket.$": "$.s3.bucket",
                                    "index.$": "States.Format('{}',$.index)",
                                    "execName.$": "$.execName",
                                    "Key.$": "$$.Map.Item.Value",
                                },
                                "ResultPath": "$.additional",
                            }
                        },
                    },
                }
            },
        )

        continue_with_existing_ddb_item = tasks.CallAwsService(
            self,
            "ListObjectsV2",
            service="s3",
            action="listObjectsV2",
            parameters={
                "Bucket": "$.bucket",
                "Prefix": "$.prefix",
            },
            result_path="$.keys",
            result_selector="$.Contents[*].['Key']",
        )
        scene_detection = self.scene_detection_definition()
        parquet_extraction = self.parquet_extraction_definition()
        start_processing = sfn.Parallel(self, "Start Processing").branch(scene_detection).branch(parquet_extraction)

        definition = dynamo_query.next(
            sfn.Choice(self, "Choice")
            .when(sfn.Condition.number_greater_than("$.ddbCount.Count", 0), continue_with_existing_ddb_item)
            .otherwise(map_each_driver.next(start_processing))
        )
        sfn.StateMachine(self, "StateMachineFromString", definition=definition)

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            apply_to_nested_stacks=True,
            suppressions=[
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-IAM4",
                        "reason": "Managed Policies are for service account roles only",
                    }
                ),
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-IAM5",
                        "reason": "Resource access restriced to ADDF resources",
                    }
                ),
            ],
        )

        def scene_detection_definition() -> sfn.IChainable:
            image_extraction_batch_job = tasks.BatchSubmitJob(
                integration_pattern=sfn.IntegrationPattern.RUN_JOB,
                job_definition=self.job_definitions["png_batch_job_def_arn"],
                job_queue_arn=self.job_queues["on_demand_job_queue"],
                job_name="test-ros-image-pipeline-png",
                array_size=sfn.JsonPath.string_at("$.executionContext.drivesCount"),
                container_overrides=tasks.BatchContainerOverrides(
                    environment={
                        "TABLE_NAME": self.tracking_table.table_name,
                        "BATCH_ID": sfn.JsonPath.string_at("$.executionContext.execName"),
                        "DEBUG": "true",
                        "IMAGE_TOPICS": ["/flir_adk/rgb_front_left/image_raw", "/flir_adk/rgb_front_right/image_raw"],
                        "DESIRED_ENCODING": "bgr8",
                        "TARGET_BUCKET": self.target_bucket.bucket_name,
                    },
                ),
            )
            get_image_directories = tasks.CallAwsService(
                self,
                service="dynamodb",
                action="query",
                parameters={
                    "TableName": self.tracking_table.table_name,
                    "KeyConditionExpression": "pk = :pk",
                    "ProjectionExpression": "resized_image_dirs",
                    "ExpressionAttributeValues": "':pk': S.$: $.executionContext.execName",
                },
                iam_resources=[self.tracking_table.table_arn],
                result_path="$.ImageDirs",
                result_selector={"S3Paths": sfn.JsonPath.stringAt("$.Items[*][*].[*][*].S")},
            )

            map = sfn.Map(
                self,
                "Map",
                items_path=sfn.JsonPath.string_at("$.ImageDirs.S3Paths"),
                item_selector={"path.$": sfn.JsonPath.string_at("$$.Map.Item.Value")},
            )
            lane_detection_sagemaker_job = tasks.CallAwsService(
                self,
                action="createProcessingJob",
                service="sagemaker",
                integration_pattern=sfn.IntegrationPattern.RUN_JOB,
                parameters={
                    "ProcessingJobName.$": sfn.JsonPath.string_at("States.Format('lanedet-{}', States.UUID())"),
                    "AppSpecification": {
                        "ContainerArguments": [
                            "--save_dir",
                            "/opt/ml/processing/output/image",
                            "--source",
                            "/opt/ml/processing/input/image",
                            "--json_path",
                            "/opt/ml/processing/output/json",
                            "--csv_path",
                            "/opt/ml/processing/output/csv",
                        ],
                        "ImageUri": self.lane_detection_config["LaneDetectionImageUri"],
                    },
                    "ProcessingResources": {
                        "ClusterConfig": {
                            "InstanceCount": 1,
                            "InstanceType": self.lane_detection_config["LaneDetectionInstanceType"],
                            "VolumeSizeInGB": 30,
                        }
                    },
                    "NetworkConfig": {
                        "VpcConfig": {"SecurityGroupIds": [self.security_group_id], "Subnets": self.private_subnet_ids}
                    },
                    "ProcessingInputs": [
                        {
                            "InputName": "data",
                            "S3Input": {
                                "LocalPath": "/opt/ml/processing/input/image",
                                "S3DataType": "S3Prefix",
                                "S3DataDistributionType": "FullyReplicated",
                                "S3InputMode": "File",
                                "S3Uri.$": sfn.JsonPath.string_at(
                                    "States.Format('" + f"s3://{self.target_bucket.bucket_name}" + "/{}/', $.path)"
                                ),
                            },
                        }
                    ],
                    "ProcessingOutputConfig": {
                        "Outputs": [
                            {
                                "OutputName": "image_output",
                                "S3Output": {
                                    "S3UploadMode": "EndOfJob",
                                    "LocalPath": "/opt/ml/processing/output/image",
                                    "S3Uri.$": sfn.JsonPath.string_at(
                                        "States.Format('"
                                        + f"s3://{self.target_bucket.bucket_name}"
                                        + "/{}_post_lane_dets/', $.path)"
                                    ),
                                },
                            },
                            {
                                "OutputName": "json_output",
                                "S3Output": {
                                    "S3UploadMode": "EndOfJob",
                                    "LocalPath": "/opt/ml/processing/output/json",
                                    "S3Uri.$": sfn.JsonPath.string_at(
                                        "States.Format('"
                                        + f"s3://{self.target_bucket.bucket_name}"
                                        + "/{}_post_lane_dets/', $.path)"
                                    ),
                                },
                            },
                            {
                                "OutputName": "csv_output",
                                "S3Output": {
                                    "S3UploadMode": "EndOfJob",
                                    "LocalPath": "/opt/ml/processing/output/csv",
                                    "S3Uri.$": sfn.JsonPath.string_at(
                                        "States.Format('"
                                        + f"s3://{self.target_bucket.bucket_name}"
                                        + "/{}_post_lane_dets/', $.path)"
                                    ),
                                },
                            },
                        ]
                    },
                    "RoleArn": self.lane_detection_config["LaneDetectionRole"],
                    "StoppingCondition": {"MaxRuntimeInSeconds": 86400},
                },
            )

            object_detection_sagemaker_job = tasks.CallAwsService(
                self,
                action="createProcessingJob",
                service="sagemaker",
                integration_pattern=sfn.IntegrationPattern.RUN_JOB,
                parameters={
                    "ProcessingJobName.$": sfn.JsonPath.string_at("States.Format('lanedet-{}', States.UUID())"),
                    "AppSpecification": {
                        "ContainerArguments": [
                            "--save_dir",
                            "/opt/ml/processing/output/image",
                            "--source",
                            "/opt/ml/processing/input/image",
                            "--json_path",
                            "/opt/ml/processing/output/json",
                            "--csv_path",
                            "/opt/ml/processing/output/csv",
                        ],
                        "ImageUri": self.object_detection_config["LaneDetectionImageUri"],
                    },
                    "ProcessingResources": {
                        "ClusterConfig": {
                            "InstanceCount": 1,
                            "InstanceType": self.object_detection_config["LaneDetectionInstanceType"],
                            "VolumeSizeInGB": 30,
                        }
                    },
                    "NetworkConfig": {
                        "VpcConfig": {"SecurityGroupIds": [self.security_group_id], "Subnets": self.private_subnet_ids}
                    },
                    "ProcessingInputs": [
                        {
                            "InputName": "data",
                            "S3Input": {
                                "LocalPath": "/opt/ml/processing/input/",
                                "S3DataDistributionType": "FullyReplicated",
                                "S3InputMode": "File",
                                "S3DataType": "S3Prefix",
                                "S3Uri.$": sfn.JsonPath.string_at(
                                    "States.Format('" + f"s3://{self.target_bucket.bucket_name}" + "/{}/', $.path)"
                                ),
                            },
                        }
                    ],
                    "ProcessingOutputConfig": {
                        "Outputs": [
                            {
                                "OutputName": "output",
                                "S3Output": {
                                    "S3UploadMode": "EndOfJob",
                                    "LocalPath": "/opt/ml/processing/output/",
                                    "S3Uri.$": sfn.JsonPath.string_at(
                                        "States.Format('"
                                        + f"s3://{self.target_bucket.bucket_name}"
                                        + "/{}_post_obj_dets/', $.path)"
                                    ),
                                },
                            }
                        ]
                    },
                    "RoleArn": self.object_detection_config["ObjectDetectionRole"],
                    "StoppingCondition": {"MaxRuntimeInSeconds": 86400},
                },
            )

            item_processor_definition = (
                sfn.Parallel(self, "Start Processing")
                .branch(lane_detection_sagemaker_job)
                .branch(object_detection_sagemaker_job)
            )

            map.item_processor(item_processor_definition)

            scene_detection_job = tasks.CallAwsService(
                self, 
                "Scene Detection",
                action="startJobRun",
                service="emr-serverless",
                integration_pattern=sfn.IntegrationPattern.RUN_JOB,
                parameters={
                    "ApplicationId": self.emr_job_config["EMRApplicationId"],
                    "ExecutionRoleArn": self.emr_job_config["EMRJobRole"],
                    "JobDriver": {
                        "SparkSubmit": {
                            "EntryPoint": f"s3://{self.target_bucket.bucket_name}/dags/aws-solutions/analysis-rip/image_dags/detect_scenes.py",
                            "EntryPointArguments.$": sfn.JsonPath.string_at("$.EMR.EMRArgs"),
                            "SparkSubmitParameters": [
                                "--jars",
                                f"s3://{self.target_bucket.bucket_name}/dags/aws-solutions/analysis-rip/image_dags/spark-dynamodb_2.12-1.1.1.jar"
                            ]
                        }
                    },
                    "ConfigurationOverrides": {
                        "MonitoringConfiguration": {
                            "Enabled": True,
                            "LogUri": "s3://addf-aws-solutions-logs-bucket-f4efdad4/scene-detection"
                        }
                    }
                },
            )

            definition = image_extraction_batch_job.next(get_image_directories).next(map).next(scene_detection_job).next(sfn.Succeed(self, "Success"))

            return sfn.Pass(self)

        def parquet_extraction_definition() -> sfn.IChainable:
            return tasks.BatchSubmitJob(
                integration_pattern=sfn.IntegrationPattern.RUN_JOB,
                job_name="test-ros-image-pipeline-parq",
                job_definition=self.job_definitions["png_batch_job_def_arn"],
                job_queue_arn=self.job_queues["on_demand_job_queue"],
                array_size=sfn.JsonPath.string_at("$.executionContext.drivesCount"),
                container_overrides=tasks.BatchContainerOverrides(
                    environment={
                        "TABLE_NAME": self.tracking_table.table_name,
                        "BATCH_ID": sfn.JsonPath.string_at("$.executionContext.execName"),
                        "DEBUG": "true",
                        "TOPICS": ["/vehicle/gps/fix", "/vehicle/gps/time", "/vehicle/gps/vel", "/imu_raw"],
                        "TARGET_BUCKET": self.target_bucket.bucket_name,
                    },
                ),
            )
