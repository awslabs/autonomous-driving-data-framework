# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
#!/usr/bin/env python3
# type: ignore
"""Script to Request Pre-signed URL from the generateUrlLambda"""

import json
import logging
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import boto3

LOGGING_FORMAT = "%(asctime)s\t%(levelname)s\t%(message)s"
LOGGING_DATEFMT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL = logging.INFO
LOGGER = {}
CONFIG_FILE_OPT = "--config-file"
SYSARGV = " ".join(sys.argv)
logging.basicConfig(format=LOGGING_FORMAT, level=LOG_LEVEL, datefmt=LOGGING_DATEFMT)
METADATA = {}


######################
# Argparser Overrides
class ScriptParser(ArgumentParser):
    """Helps manage Argparser Output"""

    def __init__(self, *args, **kwargs):
        """Constructor Override"""
        kwargs["description"] = kwargs.get("description", self.get_description())
        kwargs["usage"] = kwargs.get("usage", self.get_usage())
        super().__init__(*args, **kwargs)

    def get_description(self):
        """Override main description method"""
        return "\n".join(
            (
                "The format of the config file is:",
                "  {",
                '  "BucketName":"s3-bucket-name",',
                '  "FunctionName":"lambda-to-invoke",',
                '  "Key":"path/to/rosbag/file",',
                '  "RecordID":"record_id from DynamoDB (Partition Key)",',
                '  "SceneID":"scene_id from DynamoDB (Sort Key)"',
                "  }",
            )
        )

    def get_usage(self):
        """Override main usage method"""
        return "\n".join(
            (
                "",
                "  %(prog)s --config-file config.json",
                "  %(prog)s --bucket-name s3-bucket-name --function-name lambda-to-invoke"
                " --key path/to/rosbag/file --record record_id --scene scene_id",
                "  cat config.json | %(prog)s --config-file -",
                '  echo "{...}" | %(prog)s --config-file -',
            )
        )

    def error(self, message: str):
        """Override main error method"""
        logging.error(f"{message}\n")
        self.print_help(sys.stderr)
        sys.exit(2)


######################
# Main Execution
def main(metadata: dict):
    """Script Main Execution"""

    client = boto3.client("lambda")
    logging.info(f"Invoking: {metadata['FunctionName']}")

    payload = {
        "bucket": metadata["BucketName"],
        "key": metadata["Key"],
        "record_id": metadata["RecordID"],
        "scene_id": metadata["SceneID"],
    }
    logging.info(f"Payload: {json.dumps(payload)}")
    response = client.invoke(
        FunctionName=str(metadata["FunctionName"]),
        InvocationType="RequestResponse",
        LogType="Tail",
        Payload=json.dumps(payload),
    )

    res = json.loads(response["Payload"].read())
    status_code = int(res.get("statusCode"))
    body = json.loads(res.get("body"))

    logging.info(f"Response Status Code: {str(status_code)}")
    if status_code == 200:
        url = body.get("url")
        print(url)
    else:
        print(json.dumps(body))


if __name__ == "__main__":
    ######################
    # Parse Arguments
    parser = ScriptParser(formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument(
        CONFIG_FILE_OPT,
        dest="config_file",
        required=False,
        help='Name of the JSON file with Module\'s Metadata, use "-" to read from STDIN',
    )
    parser.add_argument(
        "--bucket-name",
        dest="bucket_name",
        required=(CONFIG_FILE_OPT not in SYSARGV),
        help="The name of the bucket containing rosbag file, required if no --config-file is provided",
    )
    parser.add_argument(
        "--function-name",
        dest="function_name",
        required=(CONFIG_FILE_OPT not in SYSARGV),
        help="The function to invoke, required if no --config-file is provided",
    )
    parser.add_argument(
        "--key",
        dest="object_key",
        required=(CONFIG_FILE_OPT not in SYSARGV),
        help="The key of the object in S3",
    )
    parser.add_argument(
        "--record",
        dest="record_id",
        required=False,
        help="The partition key of the scene in the scenario DynamoDB",
    )
    parser.add_argument(
        "--scene",
        dest="scene_id",
        required=False,
        help="The sort key of the scene in the scenario DynamoDB",
    )
    parser.add_argument("--debug", action="store_true", required=False, help="Enable Debug messages")
    arguments = parser.parse_args()

    ######################
    # Modify Logging level
    logging.getLogger().setLevel(logging.DEBUG if arguments.debug else LOG_LEVEL)

    ######################
    # Verify config file
    try:
        config_keys = ("BucketName", "FunctionName", "Key")
        if arguments.config_file is not None:
            logging.debug(f"Loading config file {arguments.config_file}")
            if arguments.config_file == "-":
                METADATA = json.load(sys.stdin)
            else:
                with open(arguments.config_file, encoding="UTF-8") as config_file:
                    METADATA = json.load(config_file)
            logging.debug(f"Config file loaded: {METADATA}")
            if not all(c_key in METADATA for c_key in config_keys):
                raise ValueError(f"Config file missing parameters: {config_keys}")
    except (ValueError, FileNotFoundError) as exc:
        logging.error(f"Error loading config file {arguments.config_file}: {exc}")
        sys.exit(1)

    ######################
    # Verify parameters
    try:
        if arguments.config_file is None:
            params_keys = ("bucket_name", "function_name", "object_key")
            if not all((p_key in arguments and getattr(arguments, p_key) != "") for p_key in params_keys):
                raise ValueError(f"Missing or empty parameters: {params_keys}")
            if (getattr(arguments, "record_id") is not None and getattr(arguments, "record_id") != "") or (
                getattr(arguments, "scene_id") is not None and getattr(arguments, "scene_id") != ""
            ):
                raise ValueError("Optional parameters should be set if any of both are declared: (record_id, scene_id)")

            METADATA = {
                "BucketName": getattr(arguments, "bucket_name"),
                "FunctionName": getattr(arguments, "function_name"),
                "Key": getattr(arguments, "object_key"),
                "RecordID": getattr(arguments, "record_id"),
                "SceneID": getattr(arguments, "scene_id"),
            }
    except (ValueError, FileNotFoundError) as exc:
        logging.error(f"Provided parameters: {arguments}")
        logging.error(f"{exc}")
        sys.exit(1)

    ######################
    # Execute
    main(metadata=METADATA)
