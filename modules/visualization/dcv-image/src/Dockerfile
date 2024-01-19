# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Copyright NI SP GmbH. All Rights Reserved.

# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Please see also https://github.com/aws-samples/aws-batch-using-nice-dcv/blob/master/aws-batch-using-nice-dcv.dockerfile

FROM public.ecr.aws/amazonlinux/amazonlinux:2 as dcv

# Prepare the container to run systemd inside
ENV container docker

# Install tools
RUN yum -y install tar sudo less vim lsof firewalld net-tools pciutils \
                   file wget kmod ca-certificates binutils kbd \
                   python3-pip bind-utils jq bc xz-utils openssl-devel libffi-devel xdg-utils

# Install X server and GNOME desktop
RUN yum -y install glx-utils mesa-dri-drivers xorg-x11-server-Xorg \
                   xorg-x11-utils xorg-x11-xauth xorg-x11-xinit  \
                   xorg*fonts* xterm libXvMC mesa-libxatracker freeglut \
                   metacity xvattr mesa-libGLU unzip dbus-x11

# Install awscliv2
RUN mkdir -p /tmp/awscli-install \
    && cd /tmp/awscli-install \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf /tmp/awscli-install

RUN rpm --import https://d1uj6qtbmh3dt5.cloudfront.net/NICE-GPG-KEY \
    && mkdir -p /tmp/dcv-inst \
    && cd /tmp/dcv-inst \
    && wget -qO- https://d1uj6qtbmh3dt5.cloudfront.net/nice-dcv-el7-x86_64.tgz |tar xfz - --strip-components=1 --no-same-owner \
    && ls -al \
    && for f in *.rpm ; do yum install -y "${f}" ; done \
    && rm -rf /tmp/dcv-inst

RUN pip3 install kubernetes urllib3==1.26.6 boto3

# Define the dcvserver.src
COPY dcvserver.service /usr/lib/systemd/system/dcvserver.service

# Copy the NICE DCV license file
COPY license.lic /etc/dcv/license.lic

# Open required port on firewall, create test user, send notification, start DCV session for the user
COPY startup_script.sh /usr/local/bin/

# Start DCV server and initialize level 5
COPY run_script.sh /usr/local/bin/

# Init session to enable X forwarding and etc
COPY init_session.sh /usr/local/bin/

# DCV configuration to avoid automatic session creation
COPY dcv.conf /etc/dcv/

# Copy the check healthy script to report Readiness
COPY check_healthy.sh /usr/local/bin/check_healthy.sh

RUN mkdir -p /opt/dcv_server/scripts

COPY update_parameters.py /opt/dcv_server/scripts

# Fix permissions
RUN chmod +x "/usr/local/bin/run_script.sh" \
             "/usr/local/bin/startup_script.sh" \
             "/usr/local/bin/init_session.sh" \
             "/usr/local/bin/check_healthy.sh"

# Expose DCV server port
EXPOSE 8443

CMD ["/usr/local/bin/run_script.sh"]
