#!/bin/bash

SECRET_NAME="aws-addf-docker-credentials"

read -p "DockerHub Username: " DOCKERHUB_USER
read -sp "DockerHub Password: " DOCKERHUB_PASS

echo -e "\nCreating Secret"

SECRET_VALUE="{\"docker.io\": { \"username\": \"$DOCKERHUB_USER\", \"password\": \"$DOCKERHUB_PASS\" }}"

EXISTS=$(aws secretsmanager describe-secret --secret-id $SECRET_NAME 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "Secret ($SECRET_NAME) exists. Updating"
    aws secretsmanager put-secret-value \
    --secret-id $SECRET_NAME \
    --secret-string "$SECRET_VALUE"

    echo "$SECRET_NAME updated"
else
    echo "Secret ($SECRET_NAME) doesn't exist. Creating"
    aws secretsmanager create-secret \
    --name $SECRET_NAME \
    --description "Credentials for DockerHub" \
    --secret-string "$SECRET_VALUE"

    echo "$SECRET_NAME created"
fi
