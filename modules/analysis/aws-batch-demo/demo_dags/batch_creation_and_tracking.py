#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License").
#    You may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import boto3
from boto3.dynamodb.conditions import Key


def add_drives_to_batch(
    table,
    src_bucket,
    max_files_per_batch,
    batch_id,
    files_in_batch,
    next_continuation,
    file_suffix,
    s3_client,
):
    drives_and_files = {}
    drive_id_batch, drive_continuation = get_batch_of_drive_ids(src_bucket, s3_client, next_continuation=next_continuation)

    for drive_id in drive_id_batch:
        if drive_id_exists(table, drive_id):
            continue
        files = get_drive_files(drive_id, src_bucket, file_suffix, s3_client)

        if files_in_batch + len(files) > max_files_per_batch:
            print(f"Adding this drive with {len(files)} files would exceed the batch size threshold")
            next_continuation = None
            break

        drives_and_files[drive_id] = files
        files_in_batch += len(files)

    batch_write_files_to_dynamo(table, drives_and_files, src_bucket, batch_id)
    return files_in_batch, next_continuation


def get_batch_of_drive_ids(src_bucket, s3_client, next_continuation=None):
    MAX_KEYS = 1000

    if next_continuation:
        response = s3_client.list_objects_v2(
            Bucket=src_bucket,
            MaxKeys=MAX_KEYS,
            Delimiter="/",
            ContinuationToken=next_continuation,
        )
    else:
        response = s3_client.list_objects_v2(Bucket=src_bucket, MaxKeys=MAX_KEYS, Delimiter="/")

    drive_ids = [x["Prefix"][0:-1] for x in response.get("CommonPrefixes", [])]
    next_continuation = response.get("NextContinuationToken")
    return drive_ids, next_continuation


def get_drive_files(drive_id, src_bucket, file_suffix, s3_client):
    MAX_KEYS = 1000
    file_response = s3_client.list_objects_v2(
        Bucket=src_bucket, Prefix=drive_id + "/", MaxKeys=MAX_KEYS, Delimiter="/"
    )
    file_next_continuation = file_response.get("NextContinuationToken")
    files = [x["Key"] for x in file_response.get("Contents", []) if x["Key"].endswith(file_suffix)]
    while file_next_continuation is not None:
        file_response = s3_client.list_objects_v2(
            Bucket=src_bucket,
            Prefix=drive_id + "/",
            MaxKeys=MAX_KEYS,
            Delimiter="/",
            ContinuationToken=file_next_continuation,
        )
        file_next_continuation = file_response.get("NextContinuationToken")
        files += [x["Key"] for x in file_response.get("Contents", [])]

    return files


def drive_id_exists(table, drive_id):
    cnt = table.query(
        KeyConditionExpression=Key("pk").eq(drive_id),
        Select="COUNT",
    )["Count"]
    return cnt > 0


def batch_write_files_to_dynamo(table, drives_and_files, src_bucket, batch_id):

    with table.batch_writer() as batch:
        idx = 0
        for drive_id, files in drives_and_files.items():
            for file in files:
                batch.put_item(
                    Item={
                        "drive_id": drive_id,
                        "file_id": file.replace(drive_id + "/", ""),
                        "s3_bucket": src_bucket,
                        "s3_key": file,
                        "pk": batch_id,
                        "sk": str(idx),
                    }
                )
                idx += 1
