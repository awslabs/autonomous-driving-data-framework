#!/bin/bash

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

exec &>> /var/log/startup_script.log

# Startup sessions
firewall-cmd --zone=public --permanent --add-port=22/tcp  # ssh standard TCP port
firewall-cmd --zone=public --permanent --add-port=8443/tcp  # DCV standard TCP port
firewall-cmd --zone=public --permanent --add-port=8443/udp  # in addition for UDP/QUIC
firewall-cmd --zone=public --permanent --add-port=10250/tcp  # in addition for TCP/k8s
firewall-cmd --reload

set -ex

export AWS_DEFAULT_REGION=${AWS_REGION}

sleep 5
mv "${HOME}/.kube/secrets" /var/run

# DCV User credentials are expected to be created in Secrets Manager
# Get username and password from aws secretsmanager
secret_value=$(aws secretsmanager get-secret-value --secret-id "$DCV_SM_NAME" 2>&1)

# Error check
if [[ $? -ne 0 ]]; then
    # Check if error indicates that secret doesn't exist
    if [[ $secret_value == *"ResourceNotFoundException"* ]]; then
        echo "Error: Secret '$DCV_SM_NAME' does not exist."
        exit 1
    else
        echo "Error retrieving secret value: $secret_value"
        exit 1
    fi
fi


# Extract UserName and Password
_username=$(echo "$secret_value" | jq --raw-output '.SecretString' | jq -r .UserName)
_passwd=$(echo "$secret_value" | jq --raw-output '.SecretString' | jq -r .Password)

# Check if _username and _passwd are not null
if [[ -z "$_username" ]]; then
    echo "Error: UserName is null or empty."
    exit 1
fi

if [[ -z "$_passwd" ]]; then
    echo "Error: Password is null or empty."
    exit 1
fi

# TODO: Enable again
adduser "${_username}"
echo "${_username}:${_passwd}" | chpasswd
sleep 5

echo "Creating session"
session_name="default-session"
/usr/bin/dcv create-session --storage-root=%home% \
                            --owner "${_username}" \
                            --init /usr/local/bin/init_session.sh \
                            --user "${_username}" \
                            --type "virtual" \
                            "${session_name}"

# Wait for sessions to be created
sleep 5

# X authenticate and update ConfigMap
echo "Authenticating session: ${session_name}"
xauth_path=$(dcv describe-session "${session_name}" | grep "X authority: ")
xauth_path=$(echo "${xauth_path}" | cut -d' ' -f 3)
display=$(dcv describe-session "${session_name}" | grep "X display: ")
display=$(echo "${display}" | cut -d' ' -f 3)
echo "XAUTHORITY is ${xauth_path}; DISPLAY is ${display}"
XAUTHORITY=${xauth_path} DISPLAY="${display}" xhost +

# if python3 /opt/dcv_server/scripts/update_parameters.py
# then
#     echo "ConfigMap and SSM Parameter Store updated"
#     mkdir -p /tmp/health-check
#     touch /tmp/health-check/ready
# else
#     echo "Unable to update ConfigMap and SSM Parameter Store"
#     exit 1
# fi

foxbox --no-sandbox &