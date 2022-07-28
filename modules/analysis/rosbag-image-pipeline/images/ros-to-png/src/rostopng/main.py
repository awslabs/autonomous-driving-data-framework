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

import argparse
import json
import logging
import os
import sys

import boto3
import cv2
import rosbag
import rospy
from cv_bridge import CvBridge

DEBUG_LOGGING_FORMAT = "[%(asctime)s][%(filename)-13s:%(lineno)3d][%(levelname)s][%(threadName)s] %(message)s"
debug = os.environ.get("DEBUG", "False").lower() in [
    "true",
    "yes",
    "1",
]
level = logging.DEBUG if debug else logging.INFO
logging.basicConfig(level=level, format=DEBUG_LOGGING_FORMAT)
logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(level)
if debug:
    logging.getLogger("boto3").setLevel(logging.ERROR)
    logging.getLogger("botocore").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("s3transfer").setLevel(logging.CRITICAL)


class VideoFromBag:
    def __init__(self, topic, images_path):
        self.bridge = CvBridge()
        output_dir = os.path.join(images_path, topic.replace("/", "_"))
        self.video = f'/tmp/{topic.replace("/", "_")}/video.mp4'
        logger.info("Get video for topic {}".format(topic))
        logger.info(
            f"""ffmpeg -r 20 -f image2 -i {output_dir}/frame_%06d.png \
            -vcodec libx264 -crf 25  -pix_fmt yuv420p {self.video}"""
        )


class ImageFromBag:
    def __init__(self, topic, encoding, bag_path, output_path):
        self.bridge = CvBridge()
        output_dir = os.path.join(output_path, topic.replace("/", "_"))
        os.makedirs(output_dir, exist_ok=True)
        files = []
        with rosbag.Bag(bag_path) as bag:
            for idx, (topic, msg, t) in enumerate(bag.read_messages(topics=[topic])):
                timestamp = "{}_{}".format(msg.header.stamp.secs, msg.header.stamp.nsecs)
                seq = "{:07d}".format(msg.header.seq)
                logger.info("Get image for frame seq {}".format(seq))
                logger.info("Get image for frame stamp {}".format(timestamp))
                cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding=encoding)
                local_image_name = "frame_{}.png".format(seq)
                s3_image_name = "frame_{}_{}.png".format(seq, timestamp)
                im_out_path = os.path.join(output_dir, local_image_name)
                logger.info("Write image: {} to {}".format(local_image_name, im_out_path))
                cv2.imwrite(im_out_path, cv_image)

                files.append(
                    {
                        "local_image_path": im_out_path,
                        "timestamp": timestamp,
                        "seq": seq,
                        "topic": topic,
                        "s3_image_name": s3_image_name,
                    }
                )
        self.files = files


def upload(client, bucket_name, drive_id, file_id, files):
    uploaded_files = []
    target_prefixes = set()
    for file in files:
        print(file)
        topic = file["topic"].replace("/", "_")
        target_prefix = os.path.join(drive_id, file_id.replace(".bag", ""), topic)
        target = os.path.join(target_prefix, file["s3_image_name"])
        print("Uploading {} to s3://{}/{}".format(file["local_image_path"], bucket_name, target))
        client.upload_file(file["local_image_path"], bucket_name, target)
        uploaded_files.append(target)
        target_prefixes.add(target_prefix)
    return uploaded_files, target_prefixes


def main(table_name, index, batch_id, bag_path, images_path, topics, encoding, target_bucket) -> int:
    logger.info("batch_id: %s", batch_id)
    logger.info("index: %s", index)
    logger.info("table_name: %s", table_name)
    logger.info("bag_path: %s", bag_path)
    logger.info("images_path: %s", images_path)
    logger.info("topics: %s", topics)
    logger.info("encoding: %s", encoding)
    logger.info("target_bucket: %s", target_bucket)

    # Getting Item to Process
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)
    item = table.get_item(
        Key={"pk": batch_id, "sk": index},
    ).get("Item", {})

    logger.info("Item Pulled: %s", item)

    if not item:
        raise Exception(f"pk: {batch_id} sk: {index} not existing in table: {table_name}")

    drive_id = item["drive_id"]
    file_id = item["file_id"]
    s3 = boto3.client("s3")

    logger.info("Downloading Bag")
    s3.download_file(item["s3_bucket"], item["s3_key"], bag_path)
    logger.info(f"Bag downloaded to {bag_path}")

    all_files = []
    for topic in topics:
        logger.info(f"Getting images from topic: {topic} with encoding {encoding}")
        try:
            bag_obj = ImageFromBag(topic, encoding, bag_path, images_path)
            all_files += bag_obj.files
            logger.info(f"Images extracted from topic: {topic} with encoding {encoding}")
            # video_file = VideoFromBag(topic, images_path)
        except rospy.ROSInterruptException:
            pass

    # Sync results
    logger.info("Uploading results")
    uploaded_files, uploaded_directories = upload(s3, target_bucket, drive_id, file_id, all_files)
    logger.info("Uploaded results")

    logger.info("Writing job status to DynamoDB")
    table.update_item(
        Key={"pk": item["drive_id"], "sk": item["file_id"]},
        UpdateExpression="SET "
        "job_status = :status, "
        "raw_image_dirs = :raw_image_dirs, "
        "raw_image_bucket = :raw_image_bucket, "
        "s3_key = :s3_key, "
        "s3_bucket = :s3_bucket,"
        "batch_id = :batch_id,"
        "array_index = :index,"
        "drive_id = :drive_id,"
        "file_id = :file_id",
        ExpressionAttributeValues={
            ":status": "success",
            ":raw_image_dirs": uploaded_directories,
            ":raw_image_bucket": target_bucket,
            ":batch_id": batch_id,
            ":index": index,
            ":s3_key": item["s3_key"],
            ":s3_bucket": item["s3_bucket"],
            ":drive_id": item["drive_id"],
            ":file_id": item["file_id"],
        },
    )

    table.update_item(
        Key={"pk": batch_id, "sk": index},
        UpdateExpression="SET "
        "job_status = :status, "
        "raw_image_dirs = :raw_image_dirs, "
        "raw_image_bucket = :raw_image_bucket, "
        "s3_key = :s3_key, "
        "s3_bucket = :s3_bucket,"
        "batch_id = :batch_id,"
        "array_index = :index",
        ExpressionAttributeValues={
            ":status": "success",
            ":raw_image_dirs": uploaded_directories,
            ":raw_image_bucket": target_bucket,
            ":batch_id": batch_id,
            ":index": index,
            ":s3_key": item["s3_key"],
            ":s3_bucket": item["s3_bucket"],
        },
    )

    return 0


if __name__ == "__main__":

    # Arguments passed from DAG Code
    parser = argparse.ArgumentParser(description="Process Files")
    parser.add_argument("--tablename", required=True)
    parser.add_argument("--index", required=True)
    parser.add_argument("--batchid", required=True)
    parser.add_argument("--localbagpath", required=True)
    parser.add_argument("--localimagespath", required=True)
    parser.add_argument("--imagetopics", required=True)
    parser.add_argument("--desiredencoding", required=True)
    parser.add_argument("--targetbucket", required=True)
    args = parser.parse_args()

    logger.debug("ARGS: %s", args)
    sys.exit(
        main(
            batch_id=args.batchid,
            index=args.index,
            table_name=args.tablename,
            bag_path=args.localbagpath,
            images_path=args.localimagespath,
            topics=json.loads(args.imagetopics),
            encoding=args.desiredencoding,
            target_bucket=args.targetbucket,
        )
    )
