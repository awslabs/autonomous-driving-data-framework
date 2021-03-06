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

#  This file is populated with configurations information when the Module is deployed
#  Configuration parameters are exported as module level constants
#
#  Example:
#  SOME_PARAMETER = 'some value'

# DUMP THESE PARAMETERS IN ../deployspec.yaml like:
# - echo "DEPLOYMENT_NAME = '${ADDF_DEPLOYMENT_NAME}'" >> demo_dags/dag_config.py

PROVIDER = "FARGATE"  # One of ON_DEMAND, SPOT, FARGATE
MAX_NUM_FILES_PER_BATCH = 1000
FILE_SUFFIX = ".bag"
VCPU = "4"
MEMORY = "16384"
CONTAINER_TIMEOUT = 180  # Seconds - must be at least 60 seconds
