import os

from main import clean_directory, process_file

if __name__ == "__main__":
    working_dir = "/tmp/working"
    output_dir = os.path.join(working_dir, "output")
    clean_directory(working_dir)
    clean_directory(output_dir)

    topics_to_extract = [
        "/gps",
        "/imu_raw",
        "/muncaster/rgb/detections_only",
        "/muncaster/thermal/detections_only",
    ]
    app_dir = os.path.dirname(os.path.abspath(__file__))
    local_file = os.path.join(app_dir, "small_2GB.bag")
    process_file(local_file, output_dir, topics_to_extract)
