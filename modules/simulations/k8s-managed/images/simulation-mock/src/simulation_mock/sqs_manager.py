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
from contextlib import contextmanager
from datetime import timedelta
from threading import Event
from typing import Iterator

from platonic.queue.errors import MessageReceiveTimeout
from platonic.sqs.queue import SQSReceiver
from platonic.sqs.queue.message import SQSMessage
from platonic.sqs.queue.types import ValueType
from platonic.timeout import ConstantTimeout
from simulation_mock import get_logger
from simulation_mock.signal_handler import SignalHandler

MESSAGE_RECEIVE_TIMEOUT_SECONDS = 10
PROCESSING_TIMEOUT_MINUTES = 5
FILE_CHECK_SLEEP_TIME_SECONDS = 10
DATA_FILE_NAME = "message.json"

LOGGER = get_logger()


class ProcessingTimeoutException(Exception):
    pass


class SQSHeartbeatReceiver(SQSReceiver[ValueType]):
    def heartbeat(self, message: SQSMessage[ValueType], seconds: int) -> None:
        """Extend the visibility timeout of Messages being processed

        Parameters
        ----------
        message : SQSMessage[ValueType]
            The SQS Message to extend
        seconds : int
            Number of seconds to extend the timeout
        """
        self.client.change_message_visibility(
            QueueUrl=self.url, ReceiptHandle=message.receipt_handle, VisibilityTimeout=seconds
        )

    @contextmanager
    def acknowledgement(self, message: SQSMessage[ValueType]) -> Iterator[SQSMessage[ValueType]]:
        """Override of ``acknowledgement`` that won't acknowledge (delete) them message if an Exception is thrown

        Parameters
        ----------
        message : SQSMessage[ValueType]
            The SQS Message to conditionally acknowledge

        Yields
        ------
        SQSMessage[ValueType]
            The SQS Message

        Raises
        ------
        e
            Any exception that was thrown
        """
        try:  # noqa: WPS501
            yield message
        except Exception as e:
            LOGGER.debug("NAK: %s - %s", message, e)
            raise e
        else:
            LOGGER.debug("ACK: %s", message)
            self.acknowledge(message)


def main(url: str, dir: str, single_message: bool) -> int:
    LOGGER.info("QUEUE: %s", url)
    LOGGER.info("DIR: %s", dir)
    LOGGER.info("SINGLE_MESSAGE: %s", single_message)
    incoming_simulations = SQSHeartbeatReceiver[str](
        url=url, timeout=ConstantTimeout(period=timedelta(seconds=MESSAGE_RECEIVE_TIMEOUT_SECONDS))
    )

    signal_handler = SignalHandler(exit=Event())
    while True:
        try:
            if signal_handler.kill_now:
                return 0
            with incoming_simulations.acknowledgement(incoming_simulations.receive()) as message:
                data_file = os.path.join(dir, "message.json")
                LOGGER.info("MSG: %s", message)
                LOGGER.info("DATA_FILE: %s", data_file)
                with open(data_file, "w") as file:
                    file.write(message.value)

                timeout = ConstantTimeout(timedelta(minutes=PROCESSING_TIMEOUT_MINUTES))
                with timeout.timer() as timer:
                    while not timer.is_expired:
                        if signal_handler.kill_now:
                            return 0
                        if os.path.isfile(data_file):
                            LOGGER.debug("EXISTS: %s", data_file)
                            incoming_simulations.heartbeat(message=message, seconds=(60))
                            signal_handler.exit.wait(FILE_CHECK_SLEEP_TIME_SECONDS)
                        else:
                            LOGGER.debug("GONE: %s", data_file)
                            break
                    else:
                        raise ProcessingTimeoutException("TIMEOUT")
        except MessageReceiveTimeout:
            LOGGER.info("EMPTY: %s", url)
            return 0
        except ProcessingTimeoutException:
            LOGGER.error("TIMEOUT: %s", PROCESSING_TIMEOUT_MINUTES)
            if single_message:
                return 1
        else:
            LOGGER.info("SUCCESS: %s", message)
            if single_message:
                return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage SQS Messages")
    parser.add_argument("--url", required=True, help="URL of the SQS Queue to manage")
    parser.add_argument("--dir", required=True, help="Directory to use/monitor for data files")
    parser.add_argument(
        "--single-message",
        action="store_true",
        help="Whether to retrieve/process a single message or process messages until the queue is empty",
    )
    args = parser.parse_args()

    LOGGER.debug("ARGS: %s", args)

    with open("/tmp/container.running", "w") as file:
        LOGGER.info("LIVENESS_FILE: /tmp/container.running")

    sys.exit(main(url=args.url, dir=args.dir, single_message=args.single_message))
