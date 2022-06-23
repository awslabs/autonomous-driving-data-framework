#!/bin/bash


export VSCODEPWD=$(echo `aws secretsmanager get-random-password --password-length 6 --exclude-punctuation --require-each-included-type  | jq '.RandomPassword'`)
aws secretsmanager create-secret \
    --name vscode-credentials \
    --description "Credentials for vscode" \
    --secret-string "{\"password\":$VSCODEPWD}"
echo "vscode-credentials created"


export JHPWD=$(echo `aws secretsmanager get-random-password --password-length 6 --exclude-punctuation --require-each-included-type  | jq '.RandomPassword'`)
aws secretsmanager create-secret \
    --name jh-credentials \
    --description "Credentials for jupyterhub" \
    --secret-string "{\"username\":\"testadmin\",\"password\":$JHPWD}"
echo "jh-credentials created"

export OSPWD=$(echo `aws secretsmanager get-random-password --password-length 6 --exclude-punctuation --require-each-included-type  | jq '.RandomPassword'`)
aws secretsmanager create-secret \
    --name opensearch-proxy-credentials \
    --description "Credentials for opensearch proxy" \
    --secret-string "{\"username\":\"addf\",\"password\":$OSPWD}"
echo "opensearch-proxy-credentials created"


    