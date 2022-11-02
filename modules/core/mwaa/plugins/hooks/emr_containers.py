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
from typing import Dict, List, Optional

from airflow.exceptions import AirflowException
from airflow.contrib.hooks.aws_hook import AwsHook


class EmrContainersHook(AwsHook):
    """
    Interact with AWS EMR Containers.


    .. seealso::
        :class:`~airflow.providers.amazon.aws.hooks.base_aws.AwsBaseHook`
    """

    def __init__(self, emr_conn_id=None, region_name=None, *args, **kwargs):
        self.emr_conn_id = emr_conn_id
        self.region_name = region_name
        self.conn = None
        super(EmrContainersHook, self).__init__(*args, **kwargs)

    def get_conn(self):
        if not self.conn:
            self.conn = self.get_client_type('emr-containers', self.region_name)
        return self.conn

