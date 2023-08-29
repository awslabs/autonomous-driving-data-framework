# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import argparse
import json
import os
import sys
import time
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

print(sys.path)
import cv2
import numpy as np
import pandas as pd
import torch
import torch.backends.cudnn as cudnn
import torchvision.transforms as transforms
from lib.config import cfg, update_config
from lib.core.function import AverageMeter
from lib.core.general import non_max_suppression, scale_coords
from lib.dataset import LoadImages, LoadStreams
from lib.models import get_net
from lib.utils import plot_one_box, show_seg_result
from lib.utils.utils import create_logger, select_device, time_synchronized
from numpy import random
from tqdm import tqdm

normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])

transform = transforms.Compose(
    [
        transforms.ToTensor(),
        normalize,
    ]
)


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


name_lanes = []


def detect(cfg, opt):

    logger, _, _ = create_logger(cfg, cfg.LOG_DIR, "demo")

    device = select_device(logger, opt.device)
    half = device.type != "cpu"  # half precision only supported on CUDA

    # Load model
    model = get_net(cfg)
    checkpoint = torch.load(opt.weights, map_location=device)
    model.load_state_dict(checkpoint["state_dict"])
    model = model.to(device)
    if half:
        model.half()  # to FP16

    # Set Dataloader
    if opt.source.isnumeric():
        cudnn.benchmark = True  # set True to speed up constant image size inference
        dataset = LoadStreams(opt.source, img_size=opt.img_size)
        _bs = len(dataset)  # batch_size
    else:
        dataset = LoadImages(opt.source, img_size=opt.img_size)
        _bs = 1  # batch_size

    # Get names and colors
    names = model.module.names if hasattr(model, "module") else model.names
    colors = [[random.randint(0, 255) for _ in range(3)] for _ in range(len(names))]

    # Run inference
    t0 = time.time()

    _vid_path, _vid_writer = None, None
    img = torch.zeros((1, 3, opt.img_size, opt.img_size), device=device)  # init img
    _ = model(img.half() if half else img) if device.type != "cpu" else None  # run once
    model.eval()

    inf_time = AverageMeter()
    nms_time = AverageMeter()

    if not os.path.exists(opt.csv_path):
        os.mkdir(opt.csv_path)

    if not os.path.exists(opt.json_path):
        os.mkdir(opt.json_path)

    for i, (path, img, img_det, vid_cap, shapes) in tqdm(enumerate(dataset), total=len(dataset)):
        img = transform(img).to(device)
        img = img.half() if half else img.float()  # uint8 to fp16/32
        if img.ndimension() == 3:
            img = img.unsqueeze(0)
        # Inference
        t1 = time_synchronized()
        det_out, da_seg_out, ll_seg_out = model(img)
        t2 = time_synchronized()

        inf_out, _ = det_out
        inf_time.update(t2 - t1, img.size(0))

        # Apply NMS
        t3 = time_synchronized()
        det_pred = non_max_suppression(
            inf_out,
            conf_thres=opt.conf_thres,
            iou_thres=opt.iou_thres,
            classes=None,
            agnostic=False,
        )
        t4 = time_synchronized()

        nms_time.update(t4 - t3, img.size(0))
        det = det_pred[0]

        save_path = (
            str(opt.save_dir + "/" + Path(path).name)
            if dataset.mode != "stream"
            else str(opt.save_dir + "/" + "web.mp4")
        )

        _, _, height, width = img.shape
        _h, _w, _ = img_det.shape
        pad_w, pad_h = shapes[1][1]
        pad_w = int(pad_w)
        pad_h = int(pad_h)
        ratio = shapes[1][0][1]

        da_predict = da_seg_out[:, :, pad_h : (height - pad_h), pad_w : (width - pad_w)]
        da_seg_mask = torch.nn.functional.interpolate(da_predict, scale_factor=int(1 / ratio), mode="bilinear")
        _, da_seg_mask = torch.max(da_seg_mask, 1)
        da_seg_mask = da_seg_mask.int().squeeze().cpu().numpy()

        ll_predict = ll_seg_out[:, :, pad_h : (height - pad_h), pad_w : (width - pad_w)]
        ll_seg_mask = torch.nn.functional.interpolate(ll_predict, scale_factor=int(1 / ratio), mode="bilinear")
        _, ll_seg_mask = torch.max(ll_seg_mask, 1)
        ll_seg_mask = ll_seg_mask.int().squeeze().cpu().numpy()
        # Lane line post-processing
        # ll_seg_mask = connect_lane(ll_seg_mask)

        img_det = show_seg_result(img_det, (da_seg_mask, ll_seg_mask), _, _, is_demo=True)

        if len(det):
            det[:, :4] = scale_coords(img.shape[2:], det[:, :4], img_det.shape).round()
            for *xyxy, conf, cls in reversed(det):
                label_det_pred = f"{names[int(cls)]} {conf:.2f}"
                plot_one_box(
                    xyxy,
                    img_det,
                    label=label_det_pred,
                    color=colors[int(cls)],
                    line_thickness=2,
                )

        # if dataset.mode == 'images':
        cv2.imwrite(save_path, img_det)

        name_lane = [Path(path).name, json.dumps(ll_seg_mask, cls=NumpyEncoder)]
        name_lanes.append(name_lane)

    df = pd.DataFrame(name_lanes, columns=["source_image", "lanes"])
    df.to_csv(path_or_buf=os.path.join(opt.csv_path, "lanes.csv"), index=False)

    print("Results saved to %s" % Path(opt.save_dir))
    print("Done. (%.3fs)" % (time.time() - t0))
    print("inf : (%.4fs/frame)   nms : (%.4fs/frame)" % (inf_time.avg, nms_time.avg))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--weights",
        nargs="+",
        type=str,
        default="weights/End-to-end.pth",
        help="model.pth path(s)",
    )
    parser.add_argument(
        "--source", type=str, default="/opt/ml/processing/input/image", help="source"
    )  # file/folder   ex:inference/images
    parser.add_argument("--img-size", type=int, default=640, help="inference size (pixels)")
    parser.add_argument("--conf-thres", type=float, default=0.25, help="object confidence threshold")
    parser.add_argument("--iou-thres", type=float, default=0.45, help="IOU threshold for NMS")
    parser.add_argument("--device", default="cpu", help="cuda device, i.e. 0 or 0,1,2,3 or cpu")
    parser.add_argument(
        "--save_dir",
        type=str,
        default="/opt/ml/processing/output/image",
        help="directory to save results",
    )
    parser.add_argument("--augment", action="store_true", help="augmented inference")
    parser.add_argument("--update", action="store_true", help="update all models")
    parser.add_argument(
        "--csv_path",
        type=str,
        default="/opt/ml/processing/output/csv",
        help="output path for csv",
    )
    parser.add_argument(
        "--json_path",
        type=str,
        default="/opt/ml/processing/output/json",
        help="output path for json",
    )
    opt = parser.parse_args()
    with torch.no_grad():
        detect(cfg, opt)
