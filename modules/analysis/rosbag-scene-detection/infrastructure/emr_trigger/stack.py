from typing import Any

import aws_cdk
import constructs
from aws_cdk import aws_dynamodb as dynamo
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda
from aws_cdk import aws_lambda_event_sources as sources
from aws_cdk import aws_sns as sns


class EmrTriggerStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        deployment_name: str,
        module_name: str,
        target_step_function_arn: str,
        source_bucket_sns: sns.Topic,
        dynamo_table: dynamo.Table,
        num_rosbag_topics: int,
        **kwargs: Any,
    ):
        super().__init__(
            scope,
            id,
            description="(SO9154) Autonomous Driving Data Framework (ADDF) - rosbag-scene-detection",
            **kwargs,
        )

        # SNS Triggered Pipeline
        lambda_code = aws_lambda.Code.from_asset("infrastructure/emr_trigger/lambda_source/")

        aws_lambda.Function(
            self,
            "SNSTriggeredLambda",
            function_name=f"addf-{deployment_name}-{module_name}-EMR-Trigger",
            code=lambda_code,
            handler="trigger.handler",
            runtime=aws_lambda.Runtime.PYTHON_3_7,
            timeout=aws_cdk.Duration.minutes(1),
            environment={
                "PIPELINE_ARN": target_step_function_arn,
                "TABLE_NAME": dynamo_table.table_name,
                "NUM_TOPICS": str(num_rosbag_topics),
            },
            initial_policy=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["states:StartExecution", "states:ListExecutions"],
                    resources=[target_step_function_arn],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
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
                ),
            ],
            events=[sources.SnsEventSource(source_bucket_sns)],
        )
