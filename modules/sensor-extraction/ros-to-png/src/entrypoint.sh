#/usr/bin/env bash

echo "Starting ROS"
source /opt/ros/noetic/setup.bash
export PYTHONPATH=$PYTHONPATH:$ROS_PACKAGE_PATH
env

echo "[$(date)] Start Image Extraction - batch $BATCH_ID, index: $AWS_BATCH_JOB_ARRAY_INDEX"
echo "[$(date)] Start Image Extraction - $IMAGE_TOPICS"
python3 main.py \
    --tablename $TABLE_NAME \
    --index $AWS_BATCH_JOB_ARRAY_INDEX \
    --batchid $BATCH_ID \
    --imagetopics "$IMAGE_TOPICS" \
    --desiredencoding $DESIRED_ENCODING \
    --targetbucket $TARGET_BUCKET
