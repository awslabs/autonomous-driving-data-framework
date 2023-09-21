from image_dags.ros_image_pipeline import *

def test_validate_config():
    input = {
        "drive2": {
            "bucket": "addf-ros-image-demo-raw-bucket-d2be7d29",
            "prefix": "rosbag-scene-detection/drive2/",
        },
    }
    validate_config(input)


def test_get_job_name():
    job_name = get_job_name("foobar")
    assert job_name.startswith("ros-image-pipeline-foobar-")
