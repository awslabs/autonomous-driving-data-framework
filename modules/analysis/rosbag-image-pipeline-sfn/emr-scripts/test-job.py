# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging

logger = logging.getLogger("emrserverless")
logger.setLevel("DEBUG")


def main() -> None:
    logger.info("Hello from EMR!")


if __name__ == "__main__":
    main()
