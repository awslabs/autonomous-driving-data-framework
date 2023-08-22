# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# The following is example code that walks thru the invocation of the model image
# in this module...it is an EXAMPLE that should be executed outside of this module

from sagemaker import get_execution_role
from sagemaker.processing import ProcessingInput, ProcessingOutput, Processor

### The following should ALL be replaced by addf env parameters
role = get_execution_role()

IMAGE_URI = "123456789012.dkr.ecr.us-east-1.amazonaws.com/lanedet:scriptprocessor"
INSTANCE_TYPE = "ml.p3.2xlarge"
BUCKET_INPUT = "somebucketin"
S3_INPUT_PATH = "images"

BUCKET_OUTPUT = "somebucketout"
S3_OUTPUT_PATH = "output"
S3_OUTPUT_PATH_JSON = "json_output"
# S3_OUTPUT_PATH_CSV = "csv_output"


### The following SHOULD NOT BE CHANGED
LOCAL_INPUT = "/opt/ml/processing/input/image"
LOCAL_OUTPUT = "/opt/ml/processing/output/image"
LOCAL_OUTPUT_JSON = "/opt/ml/processing/output/json"
LOCAL_OUTPUT_CSV = "/opt/ml/processing/output/csv"

processor = Processor(
    image_uri=IMAGE_URI,
    role=role,
    instance_count=1,
    instance_type=INSTANCE_TYPE,
    base_job_name="Lanedet-testing-processor",
)

# Run the processing job
processor.run(
    arguments=[
        "configs/laneatt/resnet34_tusimple.py",
        "--json_path",
        LOCAL_OUTPUT_JSON,
        # "--csv_path", LOCAL_OUTPUT_CSV
    ],
    inputs=[
        ProcessingInput(
            input_name="images_input",
            source=f"s3://{BUCKET_INPUT}/{S3_INPUT_PATH}",
            destination=LOCAL_INPUT,
        )
    ],
    outputs=[
        ProcessingOutput(
            output_name="image_output",
            source=LOCAL_OUTPUT,
            destination=f"s3://{BUCKET_OUTPUT}/{S3_OUTPUT_PATH}",
        ),
        ProcessingOutput(
            output_name="json_output",
            source=LOCAL_OUTPUT_JSON,
            destination=f"s3://{BUCKET_OUTPUT}/{S3_OUTPUT_PATH_JSON}",
        ),
        # ProcessingOutput(
        #     output_name='out_csv',
        #     source=LOCAL_OUTPUT_CSV,
        #     destination=f's3://{BUCKET}/{S3_OUTPUT_PATH_CSV}'),
    ],
)
