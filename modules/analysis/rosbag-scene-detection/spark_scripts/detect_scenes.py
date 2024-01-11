import argparse
import functools
import json
import sys

import boto3
import numpy
import pyspark.sql.functions as func
from pyspark.sql import SparkSession, Window
from pyspark.sql.types import StringType


def distance(p1, p2):
    a = numpy.array((p1["x"], p1["y"], 0))
    b = numpy.array((p2["x"], p2["y"], 0))
    return numpy.linalg.norm(a - b)


def get_nearest_image_point(x, y, img_pts):
    min_pt = None
    min_dist = 1000
    for i, pt in enumerate(img_pts):
        d = distance({"x": x, "y": y}, pt)
        if d < min_dist:
            min_dist = d
            min_pt = pt
            min_pt["dist"] = d
    return min_pt


def identify_nearest_lane_point(x, y, lane_points):
    """
    Given an x,y coordinate in the image, identify closest lane point per lane
    """
    v = json.loads(lane_points)["lanes_clean"]
    lanes = json.loads(v)

    nearest_pts = {}
    for idx, lane in enumerate(lanes):
        if lane:
            img_pts = lane["image_points"]
            nearest_pts[idx] = get_nearest_image_point(x, y, img_pts)

    return nearest_pts


def between_nums(x, i1, i2):
    return (i1 >= x >= i2) or (i1 <= x <= i2)


def point_in_lane(x, y, closest_points):
    is_in_lane = False
    lane = None
    for lane_idx, closest_point in closest_points.items():
        # if last_lane, then end
        if lane_idx == len(closest_points) - 1:
            continue
        next_lane_closest_point = closest_points[lane_idx + 1]
        # TODO consider y coordinates as well
        if between_nums(x, next_lane_closest_point["x"], closest_point["x"]):
            is_in_lane = True
            lane = f"between_{lane_idx}_and_{lane_idx + 1}"
            break
    return is_in_lane, lane


def is_object_in_lane(obj, lane_points):
    obj_corner_x_min = obj["x"] - obj["width"] / 2
    obj_corner_x_max = obj["x"] + obj["width"] / 2
    obj_corner_y_min = obj["y"] - obj["height"] / 2
    obj_corner_y_max = obj["y"] + obj["height"] / 2

    corners_in_lane = 0
    lanes = []
    for obj_corner in [
        (obj_corner_x_min, obj_corner_y_min),
        (obj_corner_x_max, obj_corner_y_min),
        (obj_corner_x_min, obj_corner_y_max),
        (obj_corner_x_max, obj_corner_y_max),
    ]:
        x = obj_corner[0]
        y = obj_corner[1]
        closest_points = identify_nearest_lane_point(x, y, lane_points=lane_points)
        in_lane = point_in_lane(x, y, closest_points)
        if in_lane[0]:
            corners_in_lane += 1
            lane = in_lane[1]
            if lane not in lanes:
                lanes.append(lane)
    return corners_in_lane, lanes


def obj_in_lane_detection(row):
    if row.get("rgb_right_detections_only_clean") and row.get("post_process_lane_points_rgb_front_right_clean"):
        objects_in_lane = []
        objects = json.loads(json.loads(row["rgb_right_detections_only_clean"]).get("detections_bboxes_clean", []))
        lane_points = row["post_process_lane_points_rgb_front_right_clean"]
        for o in objects:
            corners_in_lane, lanes = is_object_in_lane(obj=o, lane_points=lane_points)
            o.update(
                {
                    "corners_in_lane": corners_in_lane,
                    "lanes": lanes,
                }
            )
            if corners_in_lane:
                objects_in_lane.append(o)

        row["objects_in_lane"] = objects_in_lane
    else:
        row["objects_in_lane"] = None
    return row


def detect_scenes(synchronized_data):
    synced_rdd = synchronized_data.rdd.map(lambda row: row.asDict())
    return (
        synced_rdd.map(obj_in_lane_detection)
        .toDF()
        .select("Time", "objects_in_lane", "bag_file", "bag_file_prefix", "bag_file_bucket")
    )


def union_all(dfs):
    return functools.reduce(lambda df1, df2: df1.union(df2.select(df1.columns)), dfs)


def parse_arguments(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-metadata-table-name", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--input-bucket", required=True)
    parser.add_argument("--output-bucket", required=True)
    parser.add_argument("--output-dynamo-table", required=True)
    parser.add_argument("--region", required=True)
    return parser.parse_args(args=args)


def get_batch_file_metadata(table_name, batch_id, region):
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(table_name)
    response = table.query(KeyConditions={"BatchId": {"AttributeValueList": [batch_id], "ComparisonOperator": "EQ"}})
    data = response["Items"]
    while "LastEvaluatedKey" in response:
        response = table.query(ExclusiveStartKey=response["LastEvaluatedKey"])
        data.update(response["Items"])
    return data


def load_data(spark, input_bucket, table_name, batch_metadata):
    dfs = []
    for item in batch_metadata:
        s3_path = f"s3://{input_bucket}/{table_name}/bag_file={item['Name']}/"
        df = spark.read.option("basePath", f"s3://{input_bucket}/{table_name}/").load(s3_path)
        dfs.append(df)

    return union_all(dfs)


def write_results_s3(df, table_name, output_bucket, partition_cols=[]):
    s3_path = f"s3://{output_bucket}/{table_name}"
    df.write.mode("append").partitionBy(*partition_cols).parquet(s3_path)


def write_results_dynamo(df, output_dynamo_table, region):
    df.write.mode("append").option("tableName", output_dynamo_table).option("region", region).format("dynamodb").save()


def people_in_scenes(row):
    num_people_in_scene = 0
    objects = row["objects_in_lane"]
    if objects is not None:
        for obj in objects:
            if obj["Class"] == "person":
                num_people_in_scene += 1
        row["num_people_in_scene"] = num_people_in_scene
    return row


def summarize_person_scenes(df):
    people_in_lane = df.rdd.map(lambda row: row.asDict()).map(people_in_scenes).toDF()

    scene_state_udf = func.udf(
        lambda num, lag: "start" if num > 0 and lag == 0 else ("end" if num == 0 and lag > 0 else None),
        StringType(),
    )

    win = Window.orderBy("Time").partitionBy("bag_file", "bag_file_prefix", "bag_file_bucket")

    people_in_lane = people_in_lane.withColumn(
        "num_people_in_scene_lag1",
        func.lag(func.col("num_people_in_scene"), 1).over(win),
    ).filter("num_people_in_scene is not null and num_people_in_scene_lag1 is not null ")

    summary = (
        people_in_lane.withColumn(
            "scene_state",
            scene_state_udf(
                people_in_lane.num_people_in_scene,
                people_in_lane.num_people_in_scene_lag1,
            ),
        )
        .filter("scene_state is not null")
        .withColumn("end_time", func.lead(func.col("Time"), 1).over(win))
        .filter("scene_state = 'start'")
        .withColumnRenamed("Time", "start_time")
        .withColumnRenamed("num_people_in_scene", "num_people_in_scene_start")
        .select(
            "bag_file",
            "bag_file_prefix",
            "bag_file_bucket",
            "start_time",
            "end_time",
            "num_people_in_scene_start",
        )
        .withColumn(
            "scene_id",
            func.concat(func.col("bag_file"), func.lit("_PersonInLane_"), func.col("start_time")),
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

    return summary


def scene_metadata(df):
    return summarize_person_scenes(df)


def main(
    batch_metadata_table_name,
    batch_id,
    input_bucket,
    output_bucket,
    output_dynamo_table,
    spark,
    region,
):
    # Load files to process
    batch_metadata = get_batch_file_metadata(table_name=batch_metadata_table_name, batch_id=batch_id, region=region)

    # Load topic data from s3 and union
    synchronized_data = load_data(
        spark,
        input_bucket,
        batch_metadata=batch_metadata,
        table_name="synchronized_topics",
    )
    detected_scenes = detect_scenes(synchronized_data)

    # Save Synchronized Signals to S3
    write_results_s3(
        detected_scenes,
        table_name="scene_detections",
        output_bucket=output_bucket,
        partition_cols=["bag_file"],
    )

    scene_metadata_df = scene_metadata(detected_scenes)

    write_results_dynamo(scene_metadata_df, output_dynamo_table, region)


if __name__ == "__main__":

    spark = SparkSession.builder.appName("scene-detection").getOrCreate()

    sc = spark.sparkContext

    arguments = parse_arguments(sys.argv[1:])
    batch_metadata_table_name = arguments.batch_metadata_table_name
    batch_id = arguments.batch_id
    input_bucket = arguments.input_bucket
    output_bucket = arguments.output_bucket
    output_dynamo_table = arguments.output_dynamo_table
    region = arguments.region

    main(
        batch_metadata_table_name,
        batch_id,
        input_bucket,
        output_bucket,
        output_dynamo_table,
        spark,
        region,
    )
    sc.stop()
