#!/usr/bin/env python
import json

files = ["cdk-exports-rbac.json", "cdk-exports.json"]


def merge_cdk_exports(filename):
    result = list()
    for file in filename:
        with open(file, "r") as infile:
            result.extend(json.load(infile))

    with open("exports.json", "w") as output_file:
        json.dump(result, output_file)


if __name__ == "__main__":
    merge_cdk_exports(files)
