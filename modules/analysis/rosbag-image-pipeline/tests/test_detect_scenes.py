import os

from pyspark.sql.types import ArrayType, IntegerType

from image_dags.detect_scenes import *


def create_spark_session(port: int):
    os.environ["PYSPARK_SUBMIT_ARGS"] = '--packages "org.apache.hadoop:hadoop-aws:3.3.1" pyspark-shell'
    spark = SparkSession.builder.getOrCreate()
    hadoop_conf = spark.sparkContext._jsc.hadoopConfiguration()
    hadoop_conf.set("fs.s3a.access.key", "dummy-value")
    hadoop_conf.set("fs.s3a.secret.key", "dummy-value")
    hadoop_conf.set("fs.s3a.endpoint", f"http://127.0.0.1:{port}")
    hadoop_conf.set("fs.s3.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    return spark


def test_get_batch_file_metadata(moto_dynamodb):
    dynamodb = boto3.resource("dynamodb")
    table_name = "mytable"
    table = dynamodb.Table(table_name)
    items = [{"pk": 1}, {"pk": 2}]
    for item in items:
        table.put_item(Item=item)
    for item in items:
        result = get_batch_file_metadata(table_name, item["pk"], "us-west-2")
        assert len(result) > 0


def test_detect_scenes_parse_arguments():
    args = parse_arguments(
        [
            "--batch-metadata-table-name",
            "dummy",
            "--batch-id",
            "dummy",
            "--input-bucket",
            "mybucket",
            "--output-bucket",
            "mybucket",
            "--output-dynamo-table",
            "mytable",
            "--region",
            "us-east-1",
        ]
    )
    assert args.batch_metadata_table_name == "dummy"
    assert args.batch_id == "dummy"
    assert args.input_bucket == "mybucket"
    assert args.output_bucket == "mybucket"
    assert args.output_dynamo_table == "mytable"
    assert args.region == "us-east-1"


def test_load_lane_detection(moto_server):
    port = moto_server
    s3 = boto3.resource("s3", endpoint_url=f"http://127.0.0.1:{port}")
    # create an S3 bucket.
    bucket_name = "lane-detection-bucket"
    s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )
    object = s3.Object(
        bucket_name,
        "test-vehichle-01/this/_flir_adk_rgb_front_right_image_raw_resized_1280_720_post_lane_dets/lanes.csv",
    )
    data = b"lanes"
    object.put(Body=data)
    spark = create_spark_session(port=port)
    sample_metadata = [
        {
            "raw_image_bucket": bucket_name,
            "drive_id": "test-vehichle-01",
            "file_id": "this.jpg",
            "s3_bucket": bucket_name,
            "s3_key": "test-vehichle-01/this/_flir_adk_rgb_front_right_image_raw_resized_/1280_720_post_lane_dets/lanes.csv",
        }
    ]
    load_lane_detection(spark, sample_metadata)
    spark.stop()


def test_load_obj_detection(moto_server):
    port = moto_server
    s3 = boto3.resource("s3", endpoint_url=f"http://127.0.0.1:{port}")
    s3.create_bucket(
        Bucket="mybucket2",
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )
    object = s3.Object(
        "mybucket2",
        "test-vehichle-01/this/_flir_adk_rgb_front_right_image_raw_resized_1280_720_post_obj_dets/all_predictions.csv",
    )
    data = b"all_predictions"
    object.put(Body=data)
    spark = create_spark_session(port=port)
    sample_metadata = [
        {
            "raw_image_bucket": "mybucket2",
            "drive_id": "test-vehichle-01",
            "file_id": "this.jpg",
        }
    ]
    load_obj_detection(spark, sample_metadata)
    spark.stop()


def test_write_results_to_s3(moto_server):
    port = moto_server
    s3 = boto3.resource("s3", endpoint_url=f"http://127.0.0.1:{port}")
    s3.create_bucket(
        Bucket="outputbucket",
        CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
    )
    spark = create_spark_session(port=port)
    df = spark.createDataFrame(
        [
            (1, "foo"),
            (2, "bar"),
        ],
        ["id", "bag_file"],
    )
    write_results_s3(df, table_name="scene_detections", output_bucket="outputbucket", partition_cols=["bag_file"])
