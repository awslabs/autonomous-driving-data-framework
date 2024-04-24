#!/bin/bash -xe
###################################
#env
df -h
###################################



# Input JSQ File
export S3_JSQ_BUCKET=$ARTIFACTS_BUCKET
export S3_INPUT_FILE=$KEY
export S3_JSQ_INPUT_PREFIX="jsq_input/"
export S3_JSQ_INPUT_FULL_PATH="s3://${S3_JSQ_BUCKET}/${S3_JSQ_INPUT_PREFIX}" #bucket location for the input jsq files
export LOCAL_JSQ_INPUT_FULL_PATH="/job/jsq_input/"
# export START_RANGE=$START_RANGE
# export END_RANGE=$END_RANGE

# Setup Processed JSQ File location
PREFIX=$(echo $S3_INPUT_FILE | awk -F "." '{print $1}')
#export S3_OUTPUT_PROCESSED_JSQ_FULL_PATH="s3://${S3_JSQ_BUCKET}/jsq_processed/${PREFIX}/" #bucket location for the processed jsq files
export LOCAL_JSQ_PROCESSED_IMAGES_FULL_PATH="/job/jsq_processed_images/"

# Intermediate Location for extracted images
export LOCAL_EXTRACTED_IMAGES_FULL_PATH="/job/jsq_extracted_images/"

# Output image bucket
export S3_OUTPUT_FULL_PATH="s3://${S3_JSQ_BUCKET}/output/${PREFIX}/"

####
## Prepare local folder structure
mkdir -p $LOCAL_JSQ_INPUT_FULL_PATH
mkdir -p $LOCAL_JSQ_PROCESSED_IMAGES_FULL_PATH
mkdir -p $LOCAL_EXTRACTED_IMAGES_FULL_PATH

####
## Start Benchmark
start=`date +%s%3N`

####
## Start S3 Mountpoint
echo "Step 1: Mounting Amazon S3 Mountpoint location with JSQ & IDX files."
mount-s3 $S3_JSQ_BUCKET --prefix $S3_JSQ_INPUT_PREFIX $LOCAL_JSQ_INPUT_FULL_PATH 
ls -lah $LOCAL_JSQ_INPUT_FULL_PATH
## End S3 Mountpoint
####

####
## Extract images and upload to S3 Temp bucket 
echo "Step2: Processing jsq files to extract frames"
python3 /opt/extract_images_from_jseq.py $LOCAL_JSQ_INPUT_FULL_PATH $LOCAL_JSQ_PROCESSED_IMAGES_FULL_PATH $LOCAL_EXTRACTED_IMAGES_FULL_PATH
#python3 /opt/extract_images_from_jseq.py $LOCAL_JSQ_INPUT_FULL_PATH $LOCAL_JSQ_PROCESSED_IMAGES_FULL_PATH $LOCAL_EXTRACTED_IMAGES_FULL_PATH $START_RANGE $END_RANGE
df -h

###
## End Benchmark
end=`date +%s%3N`
echo Execution time was `expr $end - $start` milliseconds.

###
## Uploading extracted frames into the output S3 bucket
echo "Step 3: Uploading extracted frames into the output S3 bucket"
aws s3 cp $LOCAL_EXTRACTED_IMAGES_FULL_PATH $S3_OUTPUT_FULL_PATH --recursive --only-show-errors

echo "SUCCESS - Done Image Extraction"