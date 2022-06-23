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

import argparse
import os
import sys
from datetime import timedelta
from random import randint
from threading import Event

from platonic.timeout import ConstantTimeout
from simulation_mock import get_logger
from simulation_mock.signal_handler import SignalHandler

FILE_CHECK_TIMEOUT_SECONDS = 30
DATA_FILE_NAME = "message.json"
FILE_CHECK_SLEEP_TIME_SECONDS = 10

LOGGER = get_logger()


class RandomFailureException(Exception):
    pass


class FileCheckTimoutException(Exception):
    pass


def main(dir: str, max_seconds: int, failure_seed: int) -> int:
    LOGGER.info("DIR: %s", dir)
    LOGGER.info("MAX_SECONDS: %s", max_seconds)
    LOGGER.info("FAILURE_SEED: %s", failure_seed)

    signal_handler = SignalHandler(exit=Event())
    while True:
        try:
            if signal_handler.kill_now:
                return 0
            timeout = ConstantTimeout(timedelta(seconds=FILE_CHECK_TIMEOUT_SECONDS))
            with timeout.timer() as timer:
                data_file = os.path.join(dir, "message.json")
                LOGGER.info("DATA_FILE: %s", data_file)
                while not timer.is_expired:
                    if signal_handler.kill_now:
                        return 0
                    if os.path.isfile(data_file):
                        LOGGER.info("EXISTS: %s", data_file)
                        sleep_time = randint(0, max_seconds)
                        LOGGER.info("RANDOM_SLEEP: %s", sleep_time)
                        signal_handler.exit.wait(sleep_time)
                        if (randint(1, 32768) % failure_seed) == 0:
                            raise RandomFailureException("RANDOM")
                        else:
                            LOGGER.info("REMOVING: %s", data_file)
                            os.remove(data_file)
                            break
                    else:
                        LOGGER.debug("NOT_EXISTS: %s", data_file)
                        signal_handler.exit.wait(FILE_CHECK_SLEEP_TIME_SECONDS)
                else:
                    raise FileCheckTimoutException("TIMEOUT")
        except RandomFailureException:
            LOGGER.error("RANDOM_FAILURE")
            return 1
        except FileCheckTimoutException:
            LOGGER.info("EXISTS_TIMEOUT: %s", data_file)
            return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock simulation")
    parser.add_argument("--dir", required=True, help="Directory to use/monitor for data files")
    parser.add_argument("--max-seconds", required=True, type=int, help="Max runtime to execute mock simulation")
    parser.add_argument("--failure-seed", required=True, type=int, help="Seed number to determine random failures")
    args = parser.parse_args()

    LOGGER.debug("ARGS: %s", args)

    with open("/tmp/container.running", "w") as file:
        LOGGER.info("LIVENESS_FILE: /tmp/container.running")

    sys.exit(main(dir=args.dir, max_seconds=args.max_seconds, failure_seed=args.failure_seed))
