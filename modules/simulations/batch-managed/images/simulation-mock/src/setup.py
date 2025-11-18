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

from setuptools import find_packages, setup

setup(
    name="simulation-mock",
    version="0.1.0",
    author="AWS Professional Services",
    author_email="aws-proserve-opensource@amazon.com",
    project_urls={"Org Site": "https://aws.amazon.com/professional-services/"},
    packages=find_packages(include=["simulation_mock", "simulation_mock.*"]),
    python_requires=">=3.7, <3.14",
    install_requires=["boto3~=1.21.19", "platonic-sqs==1.0.1"],
    include_package_data=True,
)
