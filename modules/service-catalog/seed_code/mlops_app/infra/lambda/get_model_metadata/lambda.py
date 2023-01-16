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
    model_package_name = payload["detail"]["ModelPackageName"]
    model_package_group_name = payload["detail"]["ModelPackageGroupName"]
    s3_uri = payload["detail"]["InferenceSpecification"]["Containers"][0]["ModelDataUrl"]
    response = {}

    if model_package_approval_status == "Approved":
        print(f"[New Model Approved] Publishing new information to topic {SNS_TOPIC_ARN}")
        subject = f"[SageMaker] New Model Approved in {model_package_group_name}"
        msg = f"Model {model_package_name=} has been approved in model group {model_package_group_name=}.\n Model can be found in s3 {s3_uri=}.\n\n\nDetails: \n {json.dumps(event, indent=2)}"
        response = send_message(subject, msg)

    if model_package_approval_status == "PendingManualApproval":
        print(f"[New Model Registered] Publishing information to topic {SNS_TOPIC_ARN}")
        subject = f"[SageMaker] New Model Registered in {model_package_group_name}"
        msg = f"New model {model_package_name=} has been published in model group {model_package_group_name=} and is pending manual approval.\n Model has been saved in s3 {s3_uri=}.\n\n\nDetails: \n {json.dumps(event, indent=2)}"
        response = send_message(subject, msg)

    return response
