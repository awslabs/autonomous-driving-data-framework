#!/bin/bash

set -e

num_sessions=$(ps -ef | grep Xdcv | grep xauth | wc -l)

if [ "${num_sessions}" -ne 1 ]
then
    echo "Session creation not ready..."
    exit 1
fi

if [ ! -f /tmp/health-check/ready ]; then
    echo "ConfigMap update not ready"
    exit 1
fi

# The DCV Server is ready
exit 0
