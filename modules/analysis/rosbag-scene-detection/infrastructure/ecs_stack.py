# type: ignore
import json
from typing import Any, List, cast

import aws_cdk
import constructs
from aws_cdk import aws_dynamodb as dynamo
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_efs as efs
from aws_cdk import aws_glue as glue
from aws_cdk import aws_iam, aws_lambda, aws_logs, aws_s3
from aws_cdk import aws_s3_notifications as s3n
from aws_cdk import aws_sns as sns
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks

from .lambda_function import lambda_code


class Fargate(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        deployment_name: str,
        module_name: str,
        image_name: str,
        ecr_repository_name: str,
        environment_vars: dict,
        memory_limit_mib: int,
        cpu: int,
        timeout_minutes: int,
        s3_filters: list,
        glue_db_name: str,
        input_bucket_name: str,
        output_bucket_name: str,
        vpc_id: str,
        private_subnet_ids: List[str],
        topics_to_extract: List[str],
        rosbag_bagfile_table: str,
        rosbag_files_input_path_relative_to_s3: str,
        **kwargs: Any,
    ) -> None:
        """
        Imports the following infrastructure:
            2 S3 Buckets
                - "-in" bucket will be monitored for incoming data, and each incoming file will trigger an ECS Task
                - "-out" bucket will be the destination for saving processed data from the ECS Task
                - These bucket names are automatically passed as environment variables to your docker container
                    In your docker container, access these bucket names via:
                    import os
                    src_bucket = os.environ["s3_source"]
                    dest_bucket = os.environ["s3_destination"]
        Creates the following infrastructure:
            ECS Fargate Cluster
                - Using Fargate, this cluster will not cost any money when no tasks are running
            ECS Fargate Task
            ECS Task Role - used by the docker container
                - Read access to the "-in" bucket and write access to the "-out" bucket
            ECR Repository
                - reference to the repository hosting the service's docker image
            ECR Image
                - reference to the service's docker image in the ecr repo
            ECS Log Group for the ECS Task
                f'{image_name}-log-group'
            Step Function to execute the ECSRunFargateTask command
            Lambda Function listening for S3 Put Object events in src_bucket
                - then triggers Fargate Task for that object
        :param scope:
        :param id:
        :param image_name:
        :param image_dir:
        :param build_args:
        :param memory_limit_mib: RAM to allocate per task
        :param cpu: CPUs to allocate per task
        :param kwargs:
        """
        super().__init__(
            scope,
            id,
            **kwargs,
        )

        # Importing from ADDF Networking and Core Modules
        self.vpc_id = vpc_id
        self.vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=vpc_id,
        )

        self.private_subnets = []
        for idx, subnet_id in enumerate(private_subnet_ids):
            self.private_subnets.append(ec2.Subnet.from_subnet_id(scope=self, id=f"subnet{idx}", subnet_id=subnet_id))

        # DAG Bucket
        src_bucket = aws_s3.Bucket.from_bucket_name(self, "source-bucket", input_bucket_name)

        dest_bucket = aws_s3.Bucket.from_bucket_name(self, "destination-bucket", output_bucket_name)

        # EFS
        fs = efs.FileSystem(
            self,
            "efs",
            vpc=self.vpc,
            encrypted=True,
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
            throughput_mode=efs.ThroughputMode.BURSTING,
            performance_mode=efs.PerformanceMode.MAX_IO,
        )
        cfn_fs = cast(efs.CfnFileSystem, fs.node.default_child)
        cfn_fs.file_system_policy = aws_iam.PolicyDocument(
            statements=[
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    principals=[aws_iam.AnyPrincipal()],
                    actions=[
                        "elasticfilesystem:ClientMount",
                        "elasticfilesystem:ClientWrite",
                        "elasticfilesystem:ClientRootAccess",
                    ],
                    resources=["*"],
                    conditions={"Bool": {"elasticfilesystem:AccessedViaMountTarget": "true"}},
                ),
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.DENY,
                    principals=[aws_iam.AnyPrincipal()],
                    actions=["*"],
                    resources=["*"],
                    conditions={"Bool": {"aws:SecureTransport": "false"}},
                ),
            ]
        )

        access_point = fs.add_access_point(
            "AccessPoint",
            path="/ecs",
            create_acl=efs.Acl(owner_uid="1001", owner_gid="1001", permissions="750"),
            posix_user=efs.PosixUser(uid="1001", gid="1001"),
        )

        # Reference the DynamoDB table for tracking bag metadata
        dynamo_table = self.dynamotable = dynamo.Table.from_table_name(
            self, "dynamobagfiletable", table_name=rosbag_bagfile_table
        )

        # ECS Task Role
        arn_str = "arn:aws:s3:::"

        ecs_task_role = aws_iam.Role(
            self,
            "ecs_task_role",
            assumed_by=aws_iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[aws_iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchFullAccess")],
        )

        ecs_task_role.add_to_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "dynamodb:BatchGet*",
                    "dynamodb:DescribeStream",
                    "dynamodb:DescribeTable",
                    "dynamodb:Get*",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchWrite*",
                    "dynamodb:CreateTable",
                    "dynamodb:Delete*",
                    "dynamodb:Update*",
                    "dynamodb:PutItem",
                ],
                resources=[dynamo_table.table_arn],
            )
        )

        ecs_task_role.add_to_policy(
            aws_iam.PolicyStatement(
                actions=["s3:Get*", "s3:List*"],
                resources=[
                    f"{arn_str}{src_bucket.bucket_name}",
                    f"{arn_str}{src_bucket.bucket_name}/*",
                ],
            )
        )

        ecs_task_role.add_to_policy(
            aws_iam.PolicyStatement(
                actions=["s3:List*", "s3:PutObject*"],
                resources=[
                    f"{arn_str}{dest_bucket.bucket_name}",
                    f"{arn_str}{dest_bucket.bucket_name}/*",
                ],
            )
        )

        ecs_task_role.add_to_policy(
            aws_iam.PolicyStatement(
                actions=[
                    "elasticfilesystem:ClientMount",
                    "elasticfilesystem:ClientWrite",
                    "elasticfilesystem:DescribeMountTargets",
                ],
                resources=[access_point.access_point_arn],
            )
        )

        # Define task definition with a single container
        # The image is built & published from a local asset directory
        task_definition = ecs.FargateTaskDefinition(
            self,
            f"{image_name}_task_definition",
            family=f"addf-{deployment_name}-{module_name}-{image_name}-family",
            cpu=cpu,
            memory_limit_mib=memory_limit_mib,
            task_role=ecs_task_role,
            volumes=[
                ecs.Volume(
                    name="efs-volume",
                    efs_volume_configuration=ecs.EfsVolumeConfiguration(
                        file_system_id=fs.file_system_id,
                        transit_encryption="ENABLED",
                        authorization_config=ecs.AuthorizationConfig(
                            access_point_id=access_point.access_point_id, iam="ENABLED"
                        ),
                    ),
                )
            ],
        )

        repo = ecr.Repository.from_repository_name(self, id=id, repository_name=ecr_repository_name)

        img = ecs.EcrImage.from_ecr_repository(repository=repo, tag="latest")

        logs = ecs.LogDriver.aws_logs(
            stream_prefix="ecs",
            log_group=aws_logs.LogGroup(
                self,
                f"{image_name}-log-group",
                log_group_name=f"/ecs/{deployment_name}-{module_name}/{image_name}",
                removal_policy=aws_cdk.RemovalPolicy.DESTROY,
            ),
        )

        container_name = f"addf-{deployment_name}-{module_name}-{image_name}-container"

        container_def = task_definition.add_container(
            container_name,
            image=img,
            memory_limit_mib=memory_limit_mib,
            environment={
                "s3_source": src_bucket.bucket_name,
                "s3_destination": dest_bucket.bucket_name,
                "s3_dest_bucket_prefix": module_name,
                "topics_to_extract": topics_to_extract,
                "dynamo_table_name": dynamo_table.table_name,
            },
            logging=logs,
        )

        container_def.add_mount_points(
            ecs.MountPoint(
                container_path="/mnt/efs",
                source_volume="efs-volume",
                read_only=False,
            )
        )

        # Define an ECS cluster hosted within the requested VPC
        cluster = ecs.Cluster(
            self,
            "cluster",
            cluster_name=f"addf-{deployment_name}-{module_name}-{image_name}-cluster",
            vpc=self.vpc,
        )

        run_task = tasks.EcsRunTask(
            self,
            "fargatetask",
            assign_public_ip=False,
            subnets=ec2.SubnetSelection(subnets=self.private_subnets),
            cluster=cluster,
            launch_target=tasks.EcsFargateLaunchTarget(platform_version=ecs.FargatePlatformVersion.VERSION1_4),
            task_definition=task_definition,
            container_overrides=[
                tasks.ContainerOverride(
                    container_definition=task_definition.default_container,
                    environment=[
                        tasks.TaskEnvironmentVariable(name=k, value=sfn.JsonPath.string_at(v))
                        for k, v in environment_vars.items()
                    ],
                )
            ],
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,
            input_path=sfn.JsonPath.entire_payload,
            output_path=sfn.JsonPath.entire_payload,
            timeout=aws_cdk.Duration.minutes(timeout_minutes),
        )

        fs.connections.allow_default_port_from(run_task.connections)

        state_machine = sfn.StateMachine(
            self,
            "RunECSRosbagParser",
            state_machine_name=f"addf-{deployment_name}-{module_name}-ecsRosbagParser",
            definition=run_task,
            timeout=aws_cdk.Duration.minutes(timeout_minutes),
        )

        state_machine.grant_task_response(ecs_task_role)

        ecsTaskTriggerName = f"addf-{deployment_name}-{module_name}-ecsTaskTrigger"
        ecsTaskTriggerName = ecsTaskTriggerName[:63]
        lambda_function = aws_lambda.Function(
            self,
            "StepFunctionTrigger",
            function_name=ecsTaskTriggerName,
            code=aws_lambda.Code.from_inline(lambda_code),
            environment={
                "state_machine_arn": state_machine.state_machine_arn,
                "s3_prefixes": json.dumps([rosbag_files_input_path_relative_to_s3]),
                "s3_suffixes": json.dumps(s3_filters.get("suffix", [])),
            },
            memory_size=3008,
            timeout=aws_cdk.Duration.minutes(15),
            vpc=self.vpc,
            retry_attempts=0,
            handler="index.lambda_handler",
            runtime=aws_lambda.Runtime("python3.7", supports_inline_code=True),
        )

        lambda_function.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=["states:StartExecution"],
                resources=[state_machine.state_machine_arn],
            )
        )

        src_bucket.add_event_notification(
            aws_s3.EventType.OBJECT_CREATED,  # Event
            s3n.LambdaDestination(lambda_function),  # Dest
            aws_s3.NotificationKeyFilter(prefix=rosbag_files_input_path_relative_to_s3),
        )
        self.output_bucket_arn = dest_bucket.bucket_arn
        self.new_files_topic = sns.Topic(self, "NewFileEventNotification")
        dest_bucket.add_event_notification(
            aws_s3.EventType.OBJECT_CREATED,
            s3n.SnsDestination(self.new_files_topic),
            # aws_s3.NotificationKeyFilter(prefix=module_name),  # In future, as we share the intermediate bucket
        )
        crawler_role = aws_iam.Role(
            self,
            "GlueCrawlerRole",
            managed_policies=[
                aws_iam.ManagedPolicy.from_managed_policy_arn(
                    self,
                    id="GlueService",
                    managed_policy_arn="arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole",
                ),
                aws_iam.ManagedPolicy.from_managed_policy_arn(
                    self,
                    id="S3Access",
                    managed_policy_arn="arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
                ),
            ],
            assumed_by=aws_iam.ServicePrincipal("glue.amazonaws.com"),
        )

        glue.CfnCrawler(
            self,
            id="Crawler",
            name=f"addf-{deployment_name}-{module_name}-TopicParquetCrawler",
            role=crawler_role.role_arn,
            database_name=glue_db_name,
            schedule=None,
            targets=glue.CfnCrawler.TargetsProperty(
                s3_targets=[glue.CfnCrawler.S3TargetProperty(path=f"s3://{dest_bucket.bucket_name}/{module_name}")]
            ),
        )
