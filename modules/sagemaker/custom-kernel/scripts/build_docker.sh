# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

#!/usr/bin/env bash

aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
echo Building the Docker image...
cache_image=$IMAGE_URI
docker pull ${cache_image} 2>&1 > /dev/null || true
cd docker/$ADDF_PARAMETER_SAGEMAKER_IMAGE_NAME && docker build --progress plain --cache-from=${cache_image} -t $IMAGE_URI .
docker push $IMAGE_URI
