#!/bin/bash 

set -euo pipefail
set +x

create() {
    while IFS="" read -r image || [ -n "$image" ]
    do
    image_name=$(echo $image | awk -F ':' '{ print $1 }')
    image_tag=$(echo $image | awk -F ':' '{ print $2 }')
    if ( [[ ${image_name} =~ ^[0-9] ]] ); then
        IMAGE_ACCOUNT_ID=$(echo $image_name | awk -F '/' '{print $1}' | awk -F '.' '{print $1}')
        aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $IMAGE_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
    fi
    echo Pulling the $image
    docker pull $image
    # Setting connection with AWS ECR
    aws ecr describe-repositories --repository-names ${AWS_CODESEEDER_NAME}-${image_name} || aws ecr create-repository --repository-name ${AWS_CODESEEDER_NAME}-${image_name} --image-scanning-configuration scanOnPush=true
    aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
    # Tagging and pushing Docker images according to https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-pull-ecr-image.html
    docker tag $image $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/${AWS_CODESEEDER_NAME}-${image_name}:${image_tag}
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/${AWS_CODESEEDER_NAME}-${image_name}:${image_tag}
    # Deleting so it wouldn't cause issues with codebuild storage space for huge images
    docker rmi $image
    done < images.txt
}

destroy() {
    echo "Sorry... not working"
}

$1
