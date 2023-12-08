# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Main application"""

import json
import os
import sys

import helmparser.helm.commands as helm
from helmparser.arguments import parse_args
from helmparser.logging import logger
from helmparser.parser import parser
from helmparser.utils.utils import deep_merge

project_path = os.path.realpath(os.path.dirname(__file__))


def main() -> None:
    """Main handler"""
    args = parse_args(sys.argv[1:])

    logger.info("EKS version: %s", args.eks_version)

    logger.info(
        "EKS node AMI image version: %s",
        parser.get_ami_version(args.versions_dir, args.eks_version),
    )

    images = []

    additional_images = parser.get_additional_images(args.versions_dir, args.eks_version)

    for _, image in additional_images.items():
        images.append(image)

    updated_additional_images = {}
    for name, image in additional_images.items():
        updated_additional_images[name] = f"{args.registry_prefix}{image}"

    additional_images_json = {"additional_images": updated_additional_images}

    workloads_data = parser.get_workloads(args.versions_dir, args.eks_version)

    if args.update_helm:
        for workload, values in workloads_data.items():
            logger.info("Syncing %s", workload)
            helm.add_repo(workload, values["repository"])

        helm.update_repos()

    custom_chart_values = {}

    parsed_charts = {}
    for workload, values in workloads_data.items():
        parsed_charts[workload] = {}
        if "images" not in values:
            continue

        logger.debug("Getting %s data", workload)
        parsed_charts[workload]["chart"] = helm.show("chart", f"{workload}/{values['name']}", values["version"])

        parsed_charts[workload]["values"] = helm.show("values", f"{workload}/{values['name']}", values["version"])

        if "subcharts" in values:
            parsed_charts[workload]["subcharts"] = {}
            for subchart in values["subcharts"]:
                parsed_charts[workload]["subcharts"][subchart] = {}
                parsed_charts[workload]["subcharts"][subchart] = helm.show_subchart(
                    project_path, workload, values["name"], subchart, values["version"]
                )

    for workload, values in workloads_data.items():
        custom_chart_values[workload] = {
            "helm": {
                "name": values["name"],
                "repository": values["repository"],
                "version": values["version"],
            },
            "values": {},
        }

        logger.debug("Chart %s:", workload)

        if "images" in values:
            logger.debug("\tImages:")

            for image_name, image_data in values["images"].items():
                registry = None
                repository = None
                tag = None

                # parse registries first
                for k, v in image_data.items():
                    if k == "registry":
                        registry = parser.parse_value(parsed_charts[workload], values, image_name, v, k)

                        if registry:
                            custom_chart_values[workload]["values"] = parser.add_branch_to_dict(
                                custom_chart_values[workload]["values"],
                                v,
                                f"{args.registry_prefix}{registry}",
                            )

                        continue

                # parse repositories and tags
                for k, v in image_data.items():
                    if k == "repository":
                        if "name" in v:
                            repository = v["name"]
                            continue

                        repository = parser.parse_value(parsed_charts[workload], values, image_name, v, k)

                        repository_in_chart_values = repository
                        if not registry:
                            repository_in_chart_values = f"{args.registry_prefix}{repository}"

                        custom_chart_values[workload]["values"] = parser.add_branch_to_dict(
                            custom_chart_values[workload]["values"],
                            v,
                            repository_in_chart_values,
                        )

                        continue

                    if k == "tag":
                        tag = parser.parse_value(parsed_charts[workload], values, image_name, v, k)

                        custom_chart_values[workload]["values"] = parser.add_branch_to_dict(
                            custom_chart_values[workload]["values"], v, tag
                        )

                        continue

                # remove some values
                for k, v in image_data.items():
                    # set value to empty, e.g. digest as it will be different after push to ECR
                    if k == "remove":
                        custom_chart_values[workload]["values"] = parser.add_branch_to_dict(
                            custom_chart_values[workload]["values"], v, ""
                        )
                        continue

                image = repository
                if registry:
                    image = f"{registry}/{repository}"
                if tag:
                    image += f":{tag}"

                logger.debug("\t\t%s", image)
                images.append(image)

        logger.debug("\tCustom chart values:")
        logger.debug("\t\t%s", json.dumps(custom_chart_values[workload]))

    sorted_images = sorted(set(images))

    ami_json = {"ami": {"version": parser.get_ami_version(args.versions_dir, args.eks_version)}}
    charts_json = {"charts": custom_chart_values}

    with open(
        os.path.join(project_path, "replication-result.json"),
        "w",
        encoding="utf-8",
    ) as file:
        file.write(json.dumps(deep_merge(ami_json, charts_json, additional_images_json)))

    with open(
        os.path.join(project_path, "images.txt"),
        "w",
        encoding="utf-8",
    ) as file:
        file.write("\n".join(sorted_images))


if __name__ == "__main__":
    main()
