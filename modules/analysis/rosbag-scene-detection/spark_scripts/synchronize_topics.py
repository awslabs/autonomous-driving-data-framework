import argparse
import functools
import sys

import boto3
import pyspark.sql.functions as func
from pyspark.sql import SparkSession, Window, types


def union_all(dfs):
    column_superset = set()
    for df in dfs:
        for col in df.columns:
            column_superset.add(col)
    for df in dfs:
        for col in column_superset:
            if col not in df.columns:
                df = df.withColumn(col, func.lit(None).cast(types.NullType()))
    return functools.reduce(lambda df1, df2: df1.union(df2.select(df1.columns)), dfs)


def parse_arguments(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-metadata-table-name", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--output-bucket", required=True)
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


def load_file_path(spark, file_path, topic, bag_file):
    df = spark.read.load(file_path).withColumn("topic", func.lit(topic)).withColumn("bag_file", func.lit(bag_file))
    return df


def load_and_union_data(spark, batch_metadata):
    distinct_topics = set()
    for item in batch_metadata:
        for t in item["topics"]:
            distinct_topics.add(t)

    topic_dfs = {}

    for topic in distinct_topics:
        dfs = []
        for bag_file in batch_metadata:
            print(f"{bag_file['Name']}_{topic}")
            bag_dfs = [
                load_file_path(spark, file_path=file, topic=topic, bag_file=bag_file["Name"])
                for file in bag_file["files"]
                if topic in file
            ]
            dfs.extend(bag_dfs)
        topic_dfs[topic] = union_all(dfs)

    return topic_dfs


def join_topics(dfs, col_selection_dict):
    filtered_dfs = []
    # Take first row per topic per bag_file per second rounded
    for topic_name, topic_df in dfs.items():
        topic_col_subset = col_selection_dict[topic_name]
        if "bag_file" not in topic_col_subset:
            topic_col_subset.append("bag_file")
        filtered_dfs.append(topic_df.select(*topic_col_subset))


def write_results(df, table_name, output_bucket, partition_cols=[]):
    s3_path = f"s3://{output_bucket}/{table_name}"
    df.write.mode("append").partitionBy(*partition_cols).parquet(s3_path)


def create_json_payload(df, non_json_cols):
    json_cols = [c for c in df.columns if c not in non_json_cols]

    df = df.withColumn("payload", func.to_json(func.struct([x for x in json_cols])))

    return df.drop(*json_cols)


def transform_and_union_dfs(dfs):
    transformed_dfs = []
    for k, v in dfs.items():
        transformed_df = create_json_payload(
            v, non_json_cols=["Time", "bag_file_prefix", "bag_file_bucket", "bag_file"]
        ).withColumn("topic", func.lit(k))
        transformed_dfs.append(transformed_df)
    return union_all(transformed_dfs)


def create_master_time_df(signals_df, topics):
    """
    Explode possible timestamps for each bag file's time range
    """
    time_interval_secs = 0.1

    w = Window.partitionBy("bag_file", "bag_file_prefix", "bag_file_bucket").orderBy(func.asc("Time"))

    first_and_last_signals = (
        signals_df.withColumn("rn", func.row_number().over(w))
        .withColumn(
            "max_rn",
            func.max("rn").over(Window.partitionBy("bag_file", "bag_file_prefix", "bag_file_bucket")),
        )
        .where((func.col("rn") == func.col("max_rn")) | (func.col("rn") == 1))
        .select("bag_file", "bag_file_prefix", "bag_file_bucket", "Time", "rn")
        .groupBy("bag_file", "bag_file_prefix", "bag_file_bucket")
        .agg(func.collect_list("Time").alias("Times"))
        .collect()
    )

    def customFunction(row):

        df = spark.range(row.Times[0] / time_interval_secs, row.Times[1] / time_interval_secs).select(func.col("id"))

        return (
            df.withColumn("Time", func.expr(f"id * {time_interval_secs}"))
            .withColumn("bag_file", func.lit(row.bag_file))
            .withColumn("bag_file_prefix", func.lit(row.bag_file_prefix))
            .withColumn("bag_file_bucket", func.lit(row.bag_file_bucket))
            .drop("id")
        )

    dfs = []
    for bag_file in first_and_last_signals:
        print(bag_file)
        dfs.append(customFunction(bag_file))

    master_time_df = union_all(dfs).withColumn("source", func.lit("master_time_df").cast(types.StringType()))

    for t in topics:
        master_time_df = master_time_df.withColumn(t, func.lit(None).cast(types.StringType()))

    return master_time_df


def fill_with_last_value(df, col):
    # define the window
    w = Window.partitionBy("bag_file", "bag_file_prefix", "bag_file_bucket").orderBy(func.asc("Time"))

    last_value_column = func.last(df[col], ignorenulls=True).over(w)

    df = df.withColumn(f"{col}_clean", last_value_column)
    return df


def synchronize_signals(signals_df, topics):
    master_time_df = create_master_time_df(signals_df, topics)

    topic_signals = (
        signals_df.select("bag_file", "bag_file_prefix", "bag_file_bucket", "Time", "topic", "payload")
        .groupby("bag_file", "bag_file_prefix", "bag_file_bucket", "Time")
        .pivot("topic")
        .agg(func.first("payload"))
        .withColumn("source", func.lit("signals_df").cast(types.StringType()))
    )

    unioned_signals = master_time_df.select(*topic_signals.columns).union(topic_signals).orderBy(func.asc("Time"))

    topic_cols_clean = ["bag_file", "bag_file_prefix", "bag_file_bucket", "Time"]

    for topic in topics:
        unioned_signals = fill_with_last_value(unioned_signals, topic)
        topic_cols_clean.append(f"{topic}_clean")

    unioned_signals = unioned_signals.filter("source = 'master_time_df'").select(*topic_cols_clean)

    return unioned_signals


def synchronize_topics(topic_data):
    signals_df = transform_and_union_dfs(topic_data)
    synchronized_df = synchronize_signals(signals_df, topics=list(topic_data.keys()))

    return synchronized_df


def main(batch_metadata_table_name, batch_id, output_bucket, spark, region):
    # Load files to process
    batch_metadata = get_batch_file_metadata(table_name=batch_metadata_table_name, batch_id=batch_id, region=region)

    # Load topic data from s3 and union
    topic_data = load_and_union_data(spark, batch_metadata)
    synchronized_df = synchronize_topics(topic_data)

    # Save Synchronized Signals to S3
    write_results(
        synchronized_df,
        table_name="synchronized_topics",
        output_bucket=output_bucket,
        partition_cols=["bag_file"],
    )


if __name__ == "__main__":
    spark = SparkSession.builder.appName("synchronize-topics").getOrCreate()
    sc = spark.sparkContext

    arguments = parse_arguments(sys.argv[1:])
    batch_metadata_table_name = arguments.batch_metadata_table_name
    batch_id = arguments.batch_id
    output_bucket = arguments.output_bucket
    region = arguments.region

    main(batch_metadata_table_name, batch_id, output_bucket, spark, region)
    print(batch_metadata_table_name, batch_id, output_bucket)

    sc.stop()
