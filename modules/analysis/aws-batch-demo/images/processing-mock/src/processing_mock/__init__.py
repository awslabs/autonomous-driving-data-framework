#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License").
#    You may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import logging
import os

DEBUG_LOGGING_FORMAT = "[%(asctime)s][%(filename)-13s:%(lineno)3d][%(levelname)s][%(threadName)s] %(message)s"


def get_logger() -> logging.Logger:
    debug = os.environ.get("DEBUG", "False").lower() in [
        "true",
        "yes",
        "1",
    ]
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format=DEBUG_LOGGING_FORMAT)
    logger: logging.Logger = logging.getLogger(__name__)
    logger.setLevel(level)
    if debug:
        logging.getLogger("boto3").setLevel(logging.ERROR)
        logging.getLogger("botocore").setLevel(logging.ERROR)
        logging.getLogger("urllib3").setLevel(logging.ERROR)
    return logger
