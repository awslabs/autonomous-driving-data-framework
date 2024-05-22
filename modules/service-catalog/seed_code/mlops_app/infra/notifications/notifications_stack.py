# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from aws_cdk import Stack
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_sns as sns
from constructs import Construct


class NotificationsStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        sagemaker_project_name: str,
        sagemaker_project_id: str,
        model_package_group_name: str,
        project_short_name: str,
        env_name: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        prefix = f"{sagemaker_project_name}-{sagemaker_project_id}"
        topic_name = f"{project_short_name}-sns-{env_name}"
        new_model_topic = sns.Topic(self, topic_name, display_name=topic_name, topic_name=topic_name)

        get_metadata_function = lambda_.Function(
            self,
            f"{prefix}-model-lambda",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="lambda.handler",
            function_name=f"{project_short_name}-mpg-state-change-{env_name}",
            code=lambda_.Code.from_asset("lambda/get_model_metadata"),
            environment={
                "SNS_TOPIC_ARN": new_model_topic.topic_arn,
            },
        )

        new_model_topic.grant_publish(get_metadata_function)

        get_metadata_function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sagemaker:Describe*",
                    "sagemaker:Get*",
                ],
                resources=[
                    "*",
                ],
            ),
        )

        rule = events.Rule(
            self,
            f"{prefix}-new-model-rule",
            rule_name=f"{project_short_name}-mpg-state-change-{env_name}",
            event_pattern=events.EventPattern(
                detail={
                    "ModelPackageGroupName": [model_package_group_name],
                },
                detail_type=["SageMaker Model Package State Change"],
                source=["aws.sagemaker"],
            ),
        )
        rule.add_target(targets.LambdaFunction(get_metadata_function))
