# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os

import boto3

sm_client = boto3.client("sagemaker")
sns_client = boto3.client("sns")

SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]


def send_message(subject, msg):
    response = sns_client.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=msg,
        Subject=subject,
    )

    return response


def handler(event, context):
    payload = json.loads(json.dumps(event))
    print(payload)
    model_package_approval_status = payload["detail"]["ModelApprovalStatus"]
    model_package_group_name = payload["detail"]["ModelPackageGroupName"]
    response = {}

    if model_package_approval_status == "Approved":
        print(f"[New Model Approved] Publishing new information to topic {SNS_TOPIC_ARN}")
        subject = f"[SageMaker] New Model Approved in {model_package_group_name}"
        msg = f"Details: \n {json.dumps(event, indent=2)}"
        response = send_message(subject, msg)

    if model_package_approval_status == "PendingManualApproval":
        print(f"[New Model Registered] Publishing information to topic {SNS_TOPIC_ARN}")
        subject = f"[SageMaker] New Model Registered in {model_package_group_name}"
        msg = f"Details: \n {json.dumps(event, indent=2)}"
        response = send_message(subject, msg)

    return response
