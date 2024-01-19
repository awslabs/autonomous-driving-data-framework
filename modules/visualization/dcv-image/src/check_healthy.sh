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

set -e

num_sessions=$(ps -ef | grep Xdcv | grep xauth | wc -l)
num_sockets=$(ls /tmp/.X11-unix/ -1 | wc -l)

if [ "${num_sessions}" -ne 1 ]
then
    echo "Session creation not ready..."
    exit 1
fi

if [ ! -f /tmp/health-check/ready ]; then
    echo "ConfigMap and SSM Parameter Store failed to update..."
    exit 1
fi

if [ "${num_sockets}" -ne 1 ]
then
    echo "X11 sockets not found..."
    exit 1
fi

# The DCV Server is ready and healthy
exit 0
