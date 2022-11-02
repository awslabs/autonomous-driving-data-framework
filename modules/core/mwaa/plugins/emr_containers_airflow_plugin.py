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
from airflow.plugins_manager import AirflowPlugin
from hooks.emr_containers import *
from operators.emr_containers_start_job_run import *
from operators.emr_containers_cancel_job_run import *
from sensors.emr_containers_base import *
from sensors.emr_containers_job_run import *
                    
class PluginName(AirflowPlugin):
                    
    name = 'emr_containers_airflow_plugin'
                    
    hooks = [EmrContainersHook]
    operators = [EmrContainersStartJobRun,EmrContainersCancelJobRun]
    sensors = [EmrContainersBaseSensor,EmrContainersJobRunSensor]