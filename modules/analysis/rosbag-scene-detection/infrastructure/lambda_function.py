lambda_code = """
import boto3
import json
import time
import re
import os

state_machine_arn = os.environ['state_machine_arn']

def trigger_bag_processing(bucket, prefix):
    s3_object = dict([("bucket", bucket), ("key", prefix)])
    now = str(int(time.time()))
    name = prefix + '-sf-' + now
    name = re.sub('\W+','', name)
    print(s3_object)
    client = boto3.client('stepfunctions')
    response = client.start_execution(
        stateMachineArn=state_machine_arn,
        name=name,
        input=json.dumps(s3_object)
    )


def lambda_handler(event, context):
    print(event["Records"])
    for e in event["Records"]:
        e = e["s3"]
        bucket = e["bucket"]["name"]
        prefix = e["object"]["key"]
        print(prefix)
        to_process = False
        for filter_prefix in json.loads(os.environ['s3_prefixes']):
            if filter_prefix in prefix:
                to_process = True
        for filter_suffix in json.loads(os.environ['s3_suffixes']):
            if filter_suffix in prefix:
                to_process = True
        if to_process:
            trigger_bag_processing(bucket, prefix)
        else:
            pass
"""
