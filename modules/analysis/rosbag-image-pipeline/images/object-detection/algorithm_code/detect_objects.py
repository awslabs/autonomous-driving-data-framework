from argparse import ArgumentParser
from glob import glob as get_files
from json import dump as dump_json

import torch
from pandas import concat


def get_yolov5_prediction(model, image, input_size=1280, confidence=0.25, iou=0.45):

    model.conf = confidence  # NMS confidence threshold
    model.iou = iou  # NMS IoU threshold
    model.agnostic = False  # NMS class-agnostic
    model.multi_label = True  # NMS multiple labels per box
    model.max_det = 1000  # maximum number of detections per image

    # inference with test time augmentation
    results = model(image, augment=True)

    output = {}

    output["image_filename"] = image.replace("/opt/ml/processing/input/", "")
    output["boxe"] = results.pred[0][:, :4].tolist()  # x1, y1, x2, y2
    output["score"] = results.pred[0][:, 4].tolist()
    output["category_index"] = results.pred[0][:, 5].tolist()

    category_list = [
        "person",
        "bicycle",
        "car",
        "motorcycle",
        "airplane",
        "bus",
        "train",
        "truck",
        "boat",
        "traffic light",
        "fire hydrant",
        "stop sign",
        "parking meter",
        "bench",
        "bird",
        "cat",
        "dog",
        "horse",
        "sheep",
        "cow",
        "elephant",
        "bear",
        "zebra",
        "giraffe",
        "backpack",
        "umbrella",
        "handbag",
        "tie",
        "suitcase",
        "frisbee",
        "skis",
        "snowboard",
        "sports ball",
        "kite",
        "baseball bat",
        "baseball glove",
        "skateboard",
        "surfboard",
        "tennis racket",
        "bottle",
        "wine glass",
        "cup",
        "fork",
        "knife",
        "spoon",
        "bowl",
        "banana",
        "apple",
        "sandwich",
        "orange",
        "broccoli",
        "carrot",
        "hot dog",
        "pizza",
        "donut",
        "cake",
        "chair",
        "couch",
        "potted plant",
        "bed",
        "dining table",
        "toilet",
        "tv",
        "laptop",
        "mouse",
        "remote",
        "keyboard",
        "cell phone",
        "microwave",
        "oven",
        "toaster",
        "sink",
        "refrigerator",
        "book",
        "clock",
        "vase",
        "scissors",
        "teddy bear",
        "hair drier",
        "toothbrush",
    ]

    print(output["category_index"])

    output["category"] = [category_list[int(x)] for x in output["category_index"]]

    print(output["category"])
    model_predictions = results.pandas().xyxy[0]

    print(model_predictions.head())

    return output, model_predictions


if __name__ == "__main__":

    parser = ArgumentParser()
    parser.add_argument("--model", type=str, default="yolov5s")

    args, _ = parser.parse_known_args()

    input_data_path = "/opt/ml/processing/input/"
    output_data_path = "/opt/ml/processing/output/"
    model_name = args.model

    model = torch.hub.load("ultralytics/yolov5", model_name)  # or yolov5n - yolov5x6, custom

    images_list = [file for file in get_files(input_data_path + "*.png")]

    output = {}
    dfs = []
    for image in images_list:

        output_json, output_pandas = get_yolov5_prediction(model, image)
        image_file_name = image.replace("/opt/ml/processing/input/", "")
        image_json_name = image_file_name.replace(".png", ".json")
        image_csv_name = image_file_name.replace(".png", ".csv")
        output[image_file_name] = output_json

        with open(f"{output_data_path}{image_json_name}", "w") as file:
            dump_json(output_json, file, indent=2, separators=(",", ": "), sort_keys=False)

        output_pandas["source_image"] = image_file_name
        dfs.append(output_pandas)

    concat(dfs).to_csv(f"{output_data_path}all_predictions.csv", encoding="utf-8")
