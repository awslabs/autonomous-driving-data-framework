import os.path as osp
from argparse import ArgumentParser
from glob import glob as get_files
from json import dump as dump_json

import cv2
import numpy as np
import torch
from lanedet.datasets.process import Process
from lanedet.models.registry import build_net
from lanedet.utils.config import Config
from lanedet.utils.net_utils import load_network
from lanedet.utils.visualization import imshow_lanes
from tqdm import tqdm


class Detect(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.processes = Process(cfg.val_process, cfg)
        self.net = build_net(self.cfg)
        self.net = torch.nn.parallel.DataParallel(self.net, device_ids=range(1)).cuda()
        self.net.eval()
        load_network(self.net, self.cfg.load_from)

    def preprocess(self, img_path):
        ori_img = cv2.imread(img_path)
        img = ori_img[self.cfg.cut_height :, :, :].astype(np.float32)
        data = {"img": img, "lanes": []}
        data = self.processes(data)
        data["img"] = data["img"].unsqueeze(0)
        data.update({"img_path": img_path, "ori_img": ori_img})
        return data

    def inference(self, data):
        with torch.no_grad():
            data = self.net(data)
            data = self.net.module.get_lanes(data)
        return data

    def show(self, data):
        out_file = self.cfg.savedir
        if out_file:
            out_file = osp.join(out_file, osp.basename(data["img_path"]))
        lanes = [lane.to_array(self.cfg) for lane in data["lanes"]]
        imshow_lanes(data["ori_img"], lanes, show=self.cfg.show, out_file=out_file)

    def run(self, data):
        data = self.preprocess(data)
        data["lanes"] = self.inference(data)[0]
        if self.cfg.show or self.cfg.savedir:
            self.show(data)
        return data


if __name__ == "__main__":

    parser = ArgumentParser()
    parser.add_argument("--config", type=str)

    args, _ = parser.parse_known_args()

    input_data_path = "/opt/ml/processing/input/"
    output_data_path = "/opt/ml/processing/output/"
    model_name = "/laneatt_r18_tusimple.pth"
    model_config = "/lanedet/configs/laneatt/resnet18_tusimple.py"

    cfg = Config.fromfile(model_config)
    cfg.show = False
    cfg.savedir = output_data_path
    cfg.load_from = model_name  # 'models/resa_r34_tusimple.pth'
    detect = Detect(cfg)

    images_list = [file for file in get_files(input_data_path + "*.png")]

    output = {}
    for image in tqdm(images_list):
        prediction = detect.run(image)
        image_file_name = image.replace("/opt/ml/processing/input/", "")
        image_json_name = image_file_name.replace(".png", ".json")
        output[image_file_name] = prediction

        with open(f"{output_data_path}{image_json_name}", "w") as file:
            dump_json(prediction, file, indent=2, separators=(",", ": "), sort_keys=False)

    with open(f"{output_data_path}all_predictions.json", "w") as file:
        dump_json(output, file, indent=2, separators=(",", ": "), sort_keys=False)

    # concat(dfs).to_csv(f"{output_data_path}all_predictions.csv", encoding="utf-8")
