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

function tailDcvLog {
    echo -n "Waiting for DCV Server to initialize "
    while [[ ! -f /var/log/dcv/server.log ]] ;do
        echo -n '.'
        sleep 3
    done
    echo -n '.'
    sleep 3
    echo " OK"
    tail -f -n500 /var/log/dcv/server.log
}

# A workaround as /usr/sbin/init will clear the secrets mounted by k8s
if [ -d "/var/run/secrets" ]
then
    mkdir -p "${HOME}/.kube"
    cp -r /var/run/secrets "${HOME}/.kube"
fi

rm /tmp/.X11-unix/*

# Enable the DCV service
res1=`systemctl enable dcvserver 2>&1`

echo
echo "##########################################"
echo "NICE DCV Container starting up ... "
echo "##########################################"

echo

# Show DCV Server log in case
tailDcvLog &

# Setup user and DCV session
( sleep 10;
/usr/local/bin/startup_script.sh ;
echo
echo "##########################################"
echo "Your NICE DCV Session is ready to login to ... "
echo "##########################################"

echo
echo "To connect to DCV you have 2 options: "
echo
echo "Web browser: https://External_IP_or_Server_Name:8443 \(you can accept the security exception as there is no SSL certificate installed\) – or –"
echo
echo "DCV native client for best performance: Enter “External_IP_or_Server_Name” in the connection field (the portable DCV client can be downloaded here: https://download.nice-dcv.com/)"
echo

) &

exec /usr/sbin/init
