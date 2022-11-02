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


class EmrContainersCancelJobRun(BaseOperator):
    """
    An operator that cancels a job submitted to EMR virtual cluster.

    :param id: id of the job that needs to be cancelled. (templated)
    :type name: Optional[str]
    :param virtual_cluster_id: id of the existing EMR virtual cluster (templated)
    :type virtual_cluster_id: str
    """

    template_fields = ['id', 'virtual_cluster_id']
    ui_color = '#f9c915'

    @apply_defaults
    def __init__(
        self,
        *,
        virtual_cluster_id: str,
        id: str,
        aws_conn_id='aws_default',
        **kwargs,
    ):
        if kwargs.get('xcom_push') is not None:
            raise AirflowException("'xcom_push' was deprecated, use 'do_xcom_push' instead")
        super().__init__(**kwargs)
        self.aws_conn_id = aws_conn_id
        self.id = id
        self.virtual_cluster_id = virtual_cluster_id

    def execute(self, context):
        emr_containers_hook = EmrContainersHook(aws_conn_id=self.aws_conn_id)

        emr_containers = emr_containers_hook.get_conn()

        response = emr_containers.cancel_job_run(virtualClusterId=self.virtual_cluster_id,
                                                id=self.id)
        if self.do_xcom_push:
            context['ti'].xcom_push(key='virtual_cluster_id', value=self.virtual_cluster_id)

        if not response['ResponseMetadata']['HTTPStatusCode'] == 200:
            raise AirflowException('Cancel Job Run failed: %s' % response)
        else:
            self.log.info('Cancel Job Run success - Job Id %s and virtual cluster id %s', response['id'],
                          response['virtualClusterId'])
            return response['id']
