# The following is example code that walks thru the invocation of the model image
# in this module...it is an EXAMPLE that should be executed outside of this module

from sagemaker import get_execution_role
from sagemaker.processing import ProcessingInput, ProcessingOutput, Processor

### The following should ALL be replaced by addf env parameters
role = get_execution_role()

IMAGE_URI = "123456789012.dkr.ecr.us-east-1.amazonaws.com/yolop:smprocessor"
INSTANCE_TYPE = "ml.m5.2xlarge"
BUCKET_INPUT = "bucket-sagemaker"
S3_INPUT_PATH = "images"

BUCKET_OUTPUT = "bucket-sagemaker"
S3_OUTPUT_PATH = "output_yolop/images"
S3_OUTPUT_PATH_JSON = "output_yolop/json_output"
S3_OUTPUT_PATH_CSV = "output_yolop/csv_output"


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
    base_job_name="yolop-testing-processor",
)

# Run the processing job
processor.run(
    arguments=[
        "--save_dir",
        LOCAL_OUTPUT,
        "--source",
        LOCAL_INPUT,
        "--json_path",
        LOCAL_OUTPUT_JSON,
        "--csv_path",
        LOCAL_OUTPUT_CSV,
        # "--img-size","640" #1280
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
        ProcessingOutput(
            output_name="out_csv",
            source=LOCAL_OUTPUT_CSV,
            destination=f"s3://{BUCKET_OUTPUT}/{S3_OUTPUT_PATH_CSV}",
        ),
    ],
)
