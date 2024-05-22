"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import sys

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    DateType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

bucket = sys.argv[1]

spark = SparkSession.builder.appName("citibike").getOrCreate()

schema = StructType(
    [
        StructField("tripduration", IntegerType(), True),
        StructField("starttime", DateType(), True),
        StructField("stoptime", DateType(), True),
        StructField("start_station_id", IntegerType(), True),
        StructField("start_station_name", StringType(), True),
        StructField("start_station_lat", DoubleType(), True),
        StructField("start_station_lon", DoubleType(), True),
        StructField("end_station_id", IntegerType(), True),
        StructField("end_station_name", StringType(), True),
        StructField("end_station_lat", DoubleType(), True),
        StructField("end_station_lon", DoubleType(), True),
        StructField("bike_id", IntegerType(), True),
        StructField("usertype", StringType(), True),
        StructField("birthyear", IntegerType(), True),
        StructField("gender", IntegerType(), True),
    ]
)

df = spark.read.format("csv").option("header", "true").schema(schema).load("s3://" + bucket + "/citibike/csv/")
df.write.parquet("s3://" + bucket + "/citibike/parquet/", mode="overwrite")

#######################################
df = spark.read.format("parquet").load("s3://" + bucket + "/citibike/parquet/")
df.createOrReplaceTempView("citibike")
newdf = spark.sql("select *, extract(year from starttime) as yr,extract( month from starttime) as mo from citibike")
newdf.createOrReplaceTempView("newcitibike")

output = spark.sql("select count(*) as sum, mo from newcitibike group by mo order by sum  desc")
output.coalesce(1).write.format("csv").option("header", "true").save(
    "s3://" + bucket + "/citibike/results/ridership/", mode="overwrite"
)

output = spark.sql(
    "select start_station_name,count(start_station_name) as counts, mo from newcitibike group by start_station_name,mo order by counts desc"
)
output.coalesce(1).write.format("csv").option("header", "true").save(
    "s3://" + bucket + "/citibike/results/popular_start_stations/", mode="overwrite"
)

output = spark.sql(
    "select end_station_name,count(end_station_name) as counts, mo from newcitibike group by end_station_name,mo order by counts desc"
)
output.coalesce(1).write.format("csv").option("header", "true").save(
    "s3://" + bucket + "/citibike/results/popular_end_stations/", mode="overwrite"
)

output = spark.sql(
    "select count(birthyear) as trips,mo as month,2021-birthyear as age from newcitibike group by age,month order by trips desc"
)
output.coalesce(1).write.format("csv").option("header", "true").save(
    "s3://" + bucket + "/citibike/results/trips_by_age/", mode="overwrite"
)
