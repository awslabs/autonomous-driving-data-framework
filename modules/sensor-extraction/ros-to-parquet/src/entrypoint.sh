#/usr/bin/env bash
python3 main.py \
  --tablename $TABLE_NAME \
  --index $AWS_BATCH_JOB_ARRAY_INDEX \
  --batchid $BATCH_ID \
  --sensortopics "$TOPICS" \
  --targetbucket $TARGET_BUCKET