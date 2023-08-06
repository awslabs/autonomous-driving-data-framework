import argparse
import sys

import boto3
import pyspark.sql.functions as func
from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import aggregate, col, collect_list, concat, count, first, from_json, lit, split, sum
from pyspark.sql.types import StructType, StructField, IntegerType, DoubleType, StringType, ArrayType, 

obj_schema = StructType(
    [
        StructField("_c0", IntegerType(), True),
        StructField("xmin", DoubleType(), True),
        StructField("ymin", DoubleType(), True),
        StructField("xmax", DoubleType(), True),
        StructField("ymax", DoubleType(), True),
        StructField("confidence", DoubleType(), True),
        StructField("class", IntegerType(), True),
        StructField("name", StringType(), True),
        StructField("source_image", StringType(), True),
    ]
)


def parse_arguments(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-metadata-table-name", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--input-bucket", required=False)
    parser.add_argument("--output-bucket", required=True)
    parser.add_argument("--output-dynamo-table", required=True)
    parser.add_argument("--region", required=True)
    return parser.parse_args(args=args)


def form_object_in_lane_df(obj_df, lane_df):
    obj_lane_df = obj_df.join(lane_df, on="source_image", how="inner")
    obj_lane_df = (
        obj_lane_df.withColumn(
            "pixel_rows_at_bottom_corner", obj_lane_df["lanes"].getItem(obj_lane_df.ymax.cast(IntegerType()))
        )
        .drop("lanes")
        .drop("ymax")
    )
    obj_lane_df = obj_lane_df.withColumn(
        "sum_of_pixels_intensities_at_bottom_corner_rows",
        aggregate("pixel_rows_at_bottom_corner", lit(0), lambda acc, x: acc + x),
    ).drop("pixel_rows_at_bottom_corner")
    obj_lane_df = obj_lane_df.filter(obj_lane_df.sum_of_pixels_intensities_at_bottom_corner_rows != 0)
    obj_lane_df = obj_lane_df.withColumn("source_image_split", split("source_image", "_"))
    obj_lane_df = obj_lane_df.withColumn(
        "Time",
        concat(
            obj_lane_df["source_image_split"].getItem(2),
            lit("."),
            obj_lane_df["source_image_split"].getItem(3).substr(1, 2),
        ).cast(DoubleType()),
    )

    return obj_lane_df


def get_batch_file_metadata(table_name, batch_id, region):
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(table_name)
    response = table.query(KeyConditions={"pk": {"AttributeValueList": [batch_id], "ComparisonOperator": "EQ"}})
    data = response["Items"]
    while "LastEvaluatedKey" in response:
        response = table.query(ExclusiveStartKey=response["LastEvaluatedKey"])
        data.update(response["Items"])
    return data


def load_obj_detection(spark, batch_metadata):
    path_list = []
    for item in batch_metadata:
        path_list.append(
            f"s3://{item['raw_image_bucket']}"
            f"/{item['drive_id']}"
            f"/{item['file_id'].split('.')[0]}"
            f"/_flir_adk_rgb_front_right_image_raw_"
            f"resized_1280_720_post_obj_dets/all_predictions.csv"
        )

    df = spark.read.schema(obj_schema).option("header", True).csv(path_list)
    return df


def load_lane_detection(spark, batch_metadata):
    first_item = batch_metadata[0]
    first_path = (
        f"s3://{first_item['raw_image_bucket']}/"
        f"{first_item['drive_id']}/"
        f"{first_item['file_id'].split('.')[0]}/"
        f"_flir_adk_rgb_front_right_image_raw_resized_"
        f"1280_720_post_lane_dets/lanes.csv"
    )

    first_item_split = first_item["s3_key"].rpartition("/")
    bag_file_prefix = first_item_split[0]
    bag_file = first_item_split[2].split(".")[0]

    df = (
        spark.read.option("header", True)
        .csv(first_path)
        .withColumn("bag_file_bucket", lit(first_item["s3_bucket"]))
        .withColumn("bag_file", lit(bag_file))
        .withColumn("bag_file_prefix", lit(bag_file_prefix))
    )

    for i in range(1, len(batch_metadata)):
        item = batch_metadata[i]
        path = (
            f"s3://{item['raw_image_bucket']}/"
            f"{item['drive_id']}/"
            f"{item['file_id'].split('.')[0]}/"
            f"_flir_adk_rgb_front_right_image_raw_resized_"
            f"1280_720_post_lane_dets/lanes.csv"
        )
        item_split = item["s3_key"].rpartition("/")
        bag_file_prefix = item_split[0]
        bag_file = item_split[2].split(".")[0]

        df.union(
            spark.read.option("header", True)
            .csv(path)
            .withColumn("bag_file_bucket", lit(item["s3_bucket"]))
            .withColumn("bag_file", lit(bag_file))
            .withColumn("bag_file_prefix", lit(bag_file_prefix))
        )

    lane_schema = ArrayType(ArrayType(IntegerType()), False)
    df = df.withColumn("lanes", from_json(col("lanes"), lane_schema))

    return df


def write_results_s3(df, table_name, output_bucket, partition_cols=[]):
    s3_path = f"s3://{output_bucket}/{table_name}"
    df.write.mode("append").partitionBy(*partition_cols).parquet(s3_path)


def write_results_dynamo(df, output_dynamo_table, region):
    df.write.mode("append").option("tableName", output_dynamo_table).option("region", region).format("dynamodb").save()


def summarize_truck_in_lane_scenes(obj_lane_df):
    obj_lane_df = obj_lane_df.filter(obj_lane_df.name == "truck")
    obj_lane_df = obj_lane_df.groupby("source_image").agg(
        count("name").alias("num_trucks_in_lane"),
        first("Time").alias("Time"),
        first("bag_file_bucket").alias("bag_file_bucket"),
        first("bag_file").alias("bag_file"),
        first("bag_file_prefix").alias("bag_file_prefix"),
    )

    win = Window.orderBy("Time").partitionBy("bag_file_bucket", "bag_file", "bag_file_prefix")

    obj_lane_df = (
        obj_lane_df.withColumn("num_trucks_in_lane_lag1", func.lag(func.col("num_trucks_in_lane"), 1, 0).over(win))
        .withColumn("num_trucks_in_lane_lead1", func.lead(func.col("num_trucks_in_lane"), 1, 0).over(win))
        .filter("num_trucks_in_lane_lag1 == 0 or num_trucks_in_lane_lead1 ==0")
    )

    scene_state_udf = func.udf(
        lambda num, lag: "start" if num > 0 and lag is None else ("end" if num == 0 and lag > 0 else None),
        StringType(),
    )

    truck_in_lane_scenes_df = (
        obj_lane_df.withColumn(
            "scene_state",
            scene_state_udf(
                obj_lane_df.num_trucks_in_lane,
                obj_lane_df.num_trucks_in_lane_lag1,
            ),
        )
        .withColumn("end_time", func.lead(func.col("Time"), 1).over(win))
        .filter("num_trucks_in_lane_lag1 ==0")
        .withColumnRenamed("Time", "start_time")
        .withColumnRenamed("num_trucks_in_lane", "num_trucks_in_lane_start")
        .select(
            "bag_file",
            "bag_file_bucket",
            "bag_file_prefix",
            "start_time",
            "end_time",
            "num_trucks_in_lane_start",
        )
        .withColumn(
            "scene_id",
            func.concat(func.col("bag_file"), func.lit("_TruckInLane_"), func.col("start_time")),
        )
        .withColumn("scene_length", func.col("end_time") - func.col("start_time"))
        .withColumn(
            "topics_analyzed",
            func.lit(
                ",".join(
                    [
                        "rgb_right_detections_only_clean",
                        "post_process_lane_points_rgb_front_right_clean",
                    ]
                )
            ),
        )
    )

    return truck_in_lane_scenes_df


def main(
    batch_metadata_table_name,
    batch_id,
    # input_bucket,
    output_bucket,
    output_dynamo_table,
    spark,
    region,
):
    # Load files to process
    batch_metadata = get_batch_file_metadata(table_name=batch_metadata_table_name, batch_id=batch_id, region=region)

    # Load topic data from s3 and union
    obj_df = load_obj_detection(
        spark,
        batch_metadata=batch_metadata,
    )

    lane_df = load_lane_detection(
        spark,
        batch_metadata=batch_metadata,
    )

    obj_lane_df = form_object_in_lane_df(obj_df, lane_df)

    truck_in_lane_scenes_df = summarize_truck_in_lane_scenes(obj_lane_df)

    # Save Synchronized Signals to S3
    write_results_s3(
        truck_in_lane_scenes_df,
        table_name="scene_detections",
        output_bucket=output_bucket,
        partition_cols=["bag_file"],
    )

    write_results_dynamo(truck_in_lane_scenes_df, output_dynamo_table, region)


if __name__ == "__main__":

    spark = SparkSession.builder.appName("scene-detection").getOrCreate()

    sc = spark.sparkContext

    arguments = parse_arguments(sys.argv[1:])
    batch_metadata_table_name = arguments.batch_metadata_table_name
    batch_id = arguments.batch_id
    output_bucket = arguments.output_bucket
    output_dynamo_table = arguments.output_dynamo_table
    region = arguments.region

    main(
        batch_metadata_table_name,
        batch_id,
        # input_bucket,
        output_bucket,
        output_dynamo_table,
        spark,
        region,
    )
    sc.stop()
