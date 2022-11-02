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
import ast
from typing import Optional

from airflow.exceptions import AirflowException
from airflow.models import BaseOperator
from hooks.emr_containers import EmrContainersHook
from airflow.utils.decorators import apply_defaults


class EmrContainersStartJobRun(BaseOperator):
    """
    An operator that starts job on a existing EMR virtual cluster.

    :param name: name of the job to be run. (templated)
    :type name: Optional[str]
    :param virtual_cluster_id: id of the existing EMR virtual cluster (templated)
    :type virtual_cluster_id: str
    :param client_token: pass for idempotency.(templated)
    :type client_token: Optional[str]
    :param execution_role_arn: ARN to an IAM role that is used to run the job.
    :type execution_role_arn: str
    :param release_label: Refer to the EMR release label for the runtime version.
    :type release_label: str
    :param job_driver: TBD from API doc.
    :type job_driver: dict
    :param configuration_overrides: TBD from API doc.
    :type configuration_overrides: Optional[dict]
    :param aws_conn_id: aws connection to uses
    :type aws_conn_id: str
    """

    template_fields = ['name', 'client_token', 'virtual_cluster_id']
    ui_color = '#f9c915'

    @apply_defaults
    def __init__(
        self,
        *,
        name: Optional[str] = None,
        virtual_cluster_id: str,
        client_token: Optional[str] = None,
        execution_role_arn: str,
        release_label: str,
        job_driver: dict,
        configuration_overrides: Optional[dict] = {},
        aws_conn_id='aws_default',
        **kwargs,
    ):
        if kwargs.get('xcom_push') is not None:
            raise AirflowException("'xcom_push' was deprecated, use 'do_xcom_push' instead")
        super().__init__(**kwargs)
        self.aws_conn_id = aws_conn_id
        self.name = name
        self.virtual_cluster_id = virtual_cluster_id
        self.client_token = client_token
        self.execution_role_arn = execution_role_arn
        self.release_label = release_label
        self.job_driver = job_driver
        self.configuration_overrides = configuration_overrides

    def execute(self, context):
        emr_containers_hook = EmrContainersHook(aws_conn_id=self.aws_conn_id)
        emr_containers = emr_containers_hook.get_conn()

        response = emr_containers.start_job_run(virtualClusterId=self.virtual_cluster_id,
                                                executionRoleArn=self.execution_role_arn,
                                                releaseLabel=self.release_label, jobDriver=self.job_driver,
                                                name=self.name,
                                                clientToken=self.client_token,
                                                configurationOverrides=self.configuration_overrides)
        if self.do_xcom_push:
            context['ti'].xcom_push(key='virtual_cluster_id', value=self.virtual_cluster_id)

        if not response['ResponseMetadata']['HTTPStatusCode'] == 200:
            raise AirflowException('Start Job Run failed: %s' % response)
        else:
            self.log.info('Start Job Run success - Job Id %s and virtual cluster id %s', response['id'],
                          response['virtualClusterId'])
            return response['id']
