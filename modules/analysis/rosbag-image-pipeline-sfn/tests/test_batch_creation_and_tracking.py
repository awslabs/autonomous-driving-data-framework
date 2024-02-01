from image_dags.batch_creation_and_tracking import *


def test_get_batch_file_metadata(moto_dynamodb):
    drives_and_files = {"foo": {"files": ["dummyfile"], "bucket": "dummybucket"}}
    batch_write_files_to_dynamo(
        table=moto_dynamodb.Table("mytable"),
        drives_and_files=drives_and_files,
        batch_id=1010,
    )


def test_get_drive_files(moto_s3):
    get_drive_files(
        src_bucket="mybucket",
        src_prefix="files/",
        file_suffix=".bag",
        s3_client=moto_s3,
    )


def test_add_drives_to_batch(moto_dynamodb, moto_s3):
    table = moto_dynamodb.Table("mytable")
    drives_to_process = {
        "drive1": {"bucket": "mybucket", "prefix": "rosbag-scene-detection/drive1/"},
        "drive2": {"bucket": "mybucket", "prefix": "rosbag-scene-detection/drive2/"},
    }
    add_drives_to_batch(
        table=table,
        batch_id=1010,
        drives_to_process=drives_to_process,
        file_suffix=".bag",
        s3_client=moto_s3,
    )
