# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from argparse import ArgumentParser
from glob import glob as get_files
from json import dump as dump_json

import pandas as pd
from ultralytics import YOLO


def get_pandas(result):
    # translate boxes data from a Tensor to the List of boxes info lists
    boxes_list = result.boxes.data.tolist()
    columns = ["xmin", "ymin", "xmax", "ymax", "confidence", "class", "name"]

    # iterate through the list of boxes info and make some formatting
    for i in boxes_list:
        # add a class name as a last element
        i.append(result.names[i[5]])

    return pd.DataFrame(boxes_list, columns=columns)


def get_yolo_prediction(model, image, input_data_path, _input_size=1280, confidence=0.25, iou=0.45, max_det=1000):
    model.conf = confidence  # NMS confidence threshold
    model.iou = iou  # NMS IoU threshold
    model.agnostic = False  # NMS class-agnostic
    model.multi_label = True  # NMS multiple labels per box
    model.max_det = max_det  # maximum number of detections per image

    # inference with test time augmentation
    results = model.predict(image, augment=True)[0]

    output = {}

    output["image_filename"] = image.replace(input_data_path, "")
    output["boxes"] = results.numpy().boxes.xyxy.tolist()
    output["score"] = results.numpy().boxes.conf.tolist()
    output["category_index"] = results.numpy().boxes.cls.tolist()
    output["category"] = [results.names[x] for x in output["category_index"]]

    return output, get_pandas(results)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--model", type=str, default="yolov10s")

    args, _ = parser.parse_known_args()

    input_data_path = "/opt/ml/processing/input/"
    output_data_path = "/opt/ml/processing/output/"
    model_name = args.model

    model = YOLO(model_name)

    images_list = [file for file in get_files(input_data_path + "*.png")]

    output = {}
    dfs = []
    for image in images_list:
        output_json, output_pandas = get_yolo_prediction(model, image, input_data_path)
        image_file_name = image.replace(input_data_path, "")
        image_json_name = image_file_name.replace(".png", ".json")
        image_csv_name = image_file_name.replace(".png", ".csv")
        output[image_file_name] = output_json

        with open(f"{output_data_path}{image_json_name}", "w") as file:
            dump_json(output_json, file, indent=2, separators=(",", ": "), sort_keys=False)

        output_pandas["source_image"] = image_file_name
        dfs.append(output_pandas)

    pd.concat(dfs).to_csv(f"{output_data_path}all_predictions.csv", encoding="utf-8")
