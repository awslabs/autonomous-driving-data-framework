import datetime
import json
import logging
import os
import traceback
from urllib.parse import unquote_plus

import boto3

sfn = boto3.client("stepfunctions")
dynamo = boto3.client("dynamodb")
dynamodb = boto3.resource("dynamodb")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def parse_s3_event(s3_event):
    """
    Parse S3 Event for data relevant to the DynamoDB Batch metadata table
    :param s3_event:
    :return:
    """
    d = {
        "bucket": s3_event["s3"]["bucket"]["name"],
        "key": unquote_plus(s3_event["s3"]["object"]["key"]),
        "size": int(s3_event["s3"]["object"]["size"] / 1024),
        "s3_event": s3_event,
    }
    d["bag_file"] = [x for x in d["key"].split("/") if "bag_file=" in x][0].replace("bag_file=", "")
    d["topic"] = [x for x in d["key"].split("/")][0]
    return d


def initialize_table(table):
    """
    Initialize 'Latest' Item in DynamoDB if no LATEST item is found
    :param table:
    :return:
    """
    batch_id = str(int(datetime.datetime.now().timestamp()))
    table.put_item(
        Item={
            "BatchId": "LATEST",
            "Name": "LATEST",
            "FileSizeKb": 0,
            "NumFiles": 0,
            "BatchWindowStartTime": batch_id,
        }
    )
    return batch_id


def is_safe_to_run_new_execution(pipeline_arn, current_batch_id):
    """
    Return true if no running executions found for that BatchId and a batch can be started - avoids duplicate clusters
    :param pipeline_arn:
    :param current_batch_id:
    :return:
    """
    response = sfn.list_executions(stateMachineArn=pipeline_arn, statusFilter="RUNNING", maxResults=100).get(
        "executions", []
    )
    if [x for x in response if x["name"] == f"BatchId_{current_batch_id}"]:
        return False
    else:
        return True


def reset_batch(table, latest, pipeline_arn, execution_arn, cluster_name):
    """
    When a batch run is triggered, reset the LATEST item to start collecting files for the next batch run.
    Also add batch metadata to DynamoDB for the batch run just triggered
    :param table:
    :param latest:
    :param pipeline_arn:
    :param execution_arn:
    :param cluster_name:
    :return:
    """
    table.update_item(
        Key={
            "BatchId": "LATEST",
            "Name": "LATEST",
        },
        UpdateExpression="set FileSizeKb = :f, NumFiles = :n, BatchWindowStartTime = :t",
        ExpressionAttributeValues={
            ":f": 0,
            ":n": 0,
            ":t": int(datetime.datetime.now().timestamp()),
        },
    )

    table.put_item(
        Item={
            "BatchId": "BatchMetadata",
            "Name": str(latest["BatchWindowStartTime"]),
            "FileSizeKb": latest["FileSizeKb"],
            "NumFiles": latest["NumFiles"],
            "BatchWindowStartTime": latest["BatchWindowStartTime"],
            "BatchWindowEndTime": int(datetime.datetime.now().timestamp()),
            "PipelineArn": pipeline_arn,
            "ExecutionArn": execution_arn,
            "ClusterName": cluster_name,
        }
    )


def process_sns_message(record, table, current_batch_id):
    """
    Parse S3 event record, add metadata to DynamoDB, assign to LATEST batch, and update LATEST batch metadata
    :param record:
    :param table:
    :param current_batch_id:
    :return:
    """
    message = parse_s3_event(record)

    # Add new file to latest batch
    updated_item = table.update_item(
        Key={
            "BatchId": current_batch_id,
            "Name": message["bag_file"],
        },
        UpdateExpression="SET bag_file=:bf, files = list_append(if_not_exists(files, :empty_list), :new_object), topics = list_append(if_not_exists(topics, :empty_list), :topic)",  # noqa: E501
        ExpressionAttributeValues={
            ":empty_list": [],
            ":new_object": [f"s3://{message['bucket']}/{message['key']}"],
            ":topic": [message["topic"]],
            ":bf": message["bag_file"],
        },
        ReturnValues="ALL_NEW",
    )["Attributes"]

    # Update Latest
    latest = table.update_item(
        Key={
            "BatchId": "LATEST",
            "Name": "LATEST",
        },
        UpdateExpression="set FileSizeKb = FileSizeKb + :s, NumFiles = NumFiles + :n",
        ExpressionAttributeValues={":s": message["size"], ":n": 1},
        ReturnValues="ALL_NEW",
    )["Attributes"]

    return latest, updated_item


def should_lambda_trigger_pipeline(latest_batch, latest_bag_file):
    """
    return true if pipeline should be triggered, else false
    based on values in LATEST item
    :param latest:
    :return:
    """
    # FIXME: Trigger EMR if the latest bag_file has all of the topics in DynamoDB AND X+ number of bagfiles to process
    num_topics = int(os.environ["NUM_TOPICS"])
    min_num_bags_to_process = 2

    all_topics_in_dynamo = len(list(set(latest_bag_file["topics"]))) == num_topics
    number_of_bag_files_in_batch = latest_batch["NumFiles"] / num_topics
    return all_topics_in_dynamo and number_of_bag_files_in_batch >= min_num_bags_to_process


def trigger_pipeline(current_batch_id, pipeline_arn, cluster_name):
    """
    Triggers pipeline if there is no running execution for the given batch id
    :param current_batch_id:
    :return:
    """

    pipeline_input = json.dumps(
        {
            "ClusterConfigurationOverrides": {
                "ClusterName": cluster_name,
            },
            "StepArgumentOverrides": {
                "Synchronize Topics - PySpark Job": {"DynamoDB.BatchId": current_batch_id},
                "Scene Detection - PySpark Job": {"DynamoDB.BatchId": current_batch_id},
            },
            "BatchId": current_batch_id,
        }
    )

    if is_safe_to_run_new_execution(pipeline_arn, current_batch_id):
        execution = sfn.start_execution(
            stateMachineArn=pipeline_arn,
            input=pipeline_input,
            name=f"BatchId_{current_batch_id}",
        )
        logger.info(f"Started StateMachine {pipeline_arn} with input {pipeline_input}")
        return execution
    else:
        logger.info(f"Batch already started for {pipeline_arn} with input {pipeline_input}")
        return None


def handler(event, context):
    logger.info("Lambda metadata: {} (type = {})".format(json.dumps(event), type(event)))
    logger.info("Received {} messages".format(len(event["Records"])))
    try:
        table = dynamodb.Table(os.environ["TABLE_NAME"])

        latest = table.get_item(
            Key={
                "BatchId": "LATEST",
                "Name": "LATEST",
            }
        ).get("Item")

        if latest is None:
            current_batch_id = initialize_table(table)
        else:
            current_batch_id = str(latest["BatchWindowStartTime"])

        for sns_event in event["Records"]:
            logger.info("Parsing S3 Event")
            sns_message_records = json.loads(sns_event["Sns"]["Message"])["Records"]

            for record in sns_message_records:
                latest_batch, latest_bag_file = process_sns_message(record, table, current_batch_id)

        if should_lambda_trigger_pipeline(latest_batch, latest_bag_file):
            pipeline_arn = os.environ.get("PIPELINE_ARN", "")
            cluster_name = f"demo-scene-detection-{current_batch_id}"
            execution = trigger_pipeline(current_batch_id, pipeline_arn, cluster_name)
            if execution:
                reset_batch(
                    table,
                    latest_batch,
                    pipeline_arn,
                    execution["executionArn"],
                    cluster_name,
                )

    except Exception as e:
        trc = traceback.format_exc()
        s = "Failed parsing JSON {}: {}\n\n{}".format(str(event), str(e), trc)
        logger.error(s)
        raise e
