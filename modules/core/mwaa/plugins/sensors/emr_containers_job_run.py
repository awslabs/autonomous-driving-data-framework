#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  
#  Licensed under the Apache License, Version 2.0 (the "License").
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#  
#      http://www.apache.org/licenses/LICENSE-2.0
#  
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from typing import Any, Dict, Iterable, Optional

from sensors.emr_containers_base import EmrContainersBaseSensor
from airflow.utils.decorators import apply_defaults


class EmrContainersJobRunSensor(EmrContainersBaseSensor):
    """
    Asks for the state of the step until it reaches any of the target states.
    If it fails the sensor errors, failing the task.

    With the default target states, sensor waits step to be completed.

    :param id: id of the job that needs to be cancelled. (templated)
    :type name: Optional[str]
    :param virtual_cluster_id: id of the existing EMR virtual cluster (templated)
    :type virtual_cluster_id: str
    :param target_states: the target states, sensor waits until
        step reaches any of these states
    :type target_states: list[str]
    :param failed_states: the failure states, sensor fails when
        step reaches any of these states
    :type failed_states: list[str]
    """

    template_fields = ['id', 'virtual_cluster_id']

    @apply_defaults
    def __init__(
        self,
        *,
        id: str,
        virtual_cluster_id: str,
        target_states: Optional[Iterable[str]] = None,
        failed_states: Optional[Iterable[str]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = id
        self.virtual_cluster_id = virtual_cluster_id
        self.target_states = target_states or ['COMPLETED']
        self.failed_states = failed_states or ['CANCELLED', 'FAILED']

    def get_emr_containers_response(self) -> Dict[str, Any]:
        """
        Make an API call with boto3 and get details about the Job status.

        .. seealso::
            TBD - link o API doc for EMR containers

        :return: response
        :rtype: dict[str, Any]
        """
        emr_containers_client = self.get_hook().get_conn()

        self.log.info('Poking status for job run id: %s on virtual cluster %s', self.id, self.virtual_cluster_id)
        return emr_containers_client.describe_job_run(id=self.id, virtualClusterId=self.virtual_cluster_id)

    @staticmethod
    def state_from_response(response: Dict[str, Any]) -> str:
        """
        Get state from response dictionary.

        :param response: response from AWS API
        :type response: dict[str, Any]
        :return: execution state of the cluster step
        :rtype: str
        """
        return response['jobRun']['state']

    @staticmethod
    def failure_message_from_response(response: Dict[str, Any]) -> Optional[str]:
        """
        Get failure message from response dictionary.

        :param response: response from AWS API
        :type response: dict[str, Any]
        :return: failure message
        :rtype: Optional[str]
        """
        try:
           failure_details = response['jobRun']['failureReason']
        except KeyError:
            failure_details = "Reason Not returned"
        if failure_details:
            return 'for reason {} '.format(failure_details)
        return None
