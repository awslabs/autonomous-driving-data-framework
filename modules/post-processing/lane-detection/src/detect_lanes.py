import argparse
import csv
import glob
import json
import os
import os.path as osp
from pathlib import Path

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
        data["lanes_clean"] = {idx: lane.to_array(self.cfg).tolist() for idx, lane in enumerate(data["lanes"])}
        if self.cfg.show or self.cfg.savedir:
            self.show(data)
        return data


def get_img_paths(path):
    p = str(Path(path).absolute())  # os-agnostic absolute path
    if "*" in p:
        paths = sorted(glob.glob(p, recursive=True))  # glob
    elif os.path.isdir(p):
        paths = sorted(glob.glob(os.path.join(p, "*.*")))  # dir
    elif os.path.isfile(p):
        paths = [p]  # files
    else:
        raise Exception(f"ERROR: {p} does not exist")
    return paths


def _to_json_dict_with_strings(dictionary):
    if type(dictionary) != dict:
        return str(dictionary)
    d = {k: _to_json_dict_with_strings(v) for k, v in dictionary.items()}
    return d


def to_json(dic):
    if type(dic) is dict:
        dic = dict(dic)
    else:
        dic = dic.__dict__
    return _to_json_dict_with_strings(dic)


def process(args):
    cfg = Config.fromfile(args.config)
    cfg.show = args.show
    cfg.savedir = args.savedir
    cfg.load_from = args.load_from
    # input_dir=args.load_from
    json_output = args.json_path
    csv_output = args.csv_path
    detect = Detect(cfg)
    paths = get_img_paths(args.img)
    fields = ["img_name", "lanes_clean"]
    for p in tqdm(paths):
        out = detect.run(p)
        n = p.split("/")[-1]
        if json_output:
            # json_o = f"{p[0:p.rindex('.')].replace(input_dir,json_output)}.json"
            json_o = f"{json_output}/{n.split('.')[0]}.json"
            print(json_o)
            with open(json_o, "w", encoding="utf-8") as jsonf:
                json.dump(out["lanes_clean"], jsonf)
                # REF:  https://discuss.pytorch.org/t/typeerror-tensor-is-not-json-serializable/36065/4
        if csv_output:
            # csv_o = f"{p[0:p.rindex('.')].replace(input_dir,csv_output)}.csv"
            csv_o = f"{csv_output}/{n.split('.')[0]}.csv"
            with open(csv_o, "w") as f:
                write = csv.writer(f)
                write.writerow(fields)
                write.writerows([out])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config",
        default="configs/laneatt/resnet34_tusimple.py",
        help="The path of config file",
    )
    parser.add_argument(
        "--img",
        default="/opt/ml/processing/input/image",
        help="The path of the img (img file or img_folder), for example: data/*.png",
    )
    parser.add_argument(
        "--savedir",
        type=str,
        default="/opt/ml/processing/output/image",
        help="The root of save directory",
    )
    parser.add_argument(
        "--load_from",
        type=str,
        default="models/laneatt_r34_tusimple.pth",
        help="The path of model",
    )
    parser.add_argument("--json_path", type=str, default=None, help="The root of save directory of json")
    parser.add_argument("--csv_path", type=str, default=None, help="The root of save directory of csv")
    parser.add_argument("--show", action="store_true", help="Whether to show the image")
    args = parser.parse_args()
    process(args)
