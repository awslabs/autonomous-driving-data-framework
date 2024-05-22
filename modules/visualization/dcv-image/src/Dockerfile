FROM nvcr.io/nvidia-hpcvis/paraview:egl-py3-5.11.0

ENV DISPLAY=:0 
ENV DEBIAN_FRONTEND=noninteractive
ENV GNOME_SHELL_SESSION_MODE=ubuntu
ENV XDG_CURRENT_DESKTOP=ubuntu:GNOME
ENV XDG_CONFIG_DIRS=/etc/xdg/xdg-ubuntu:/etc/xdg

# Update and install required packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        wget \
        curl \
        apt-utils \
        pkg-config \
        dconf-editor \
        gcc \
        xserver-xorg-video-nvidia-535 \
        x11-apps \
        python3 \
        python3-pip \
        firefox \
        ubuntu-desktop \
        gdm3 \
        gpg-agent \
    && rm -rf /var/lib/apt/lists/*

# Install Ubuntu Desktop
# RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
#     ubuntu-desktop \
#     gdm3 \
#     gpg-agent
# RUN apt-get install -y --no-install-recommends \
#     ubuntu-desktop \
#     gdm3 \
#     gpg-agent
RUN dpkg-reconfigure gdm3

# RUN systemctl isolate multi-user.target
# RUN systemctl isolate multi-user.target
# RUN dcvstartx &
# ADD custom.conf /etc/gdm3/custom.conf
# WORKDIR /app
# RUN apt upgrade -y

# Install NiceDCV
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
    && apt-get install -y --no-install-recommends \
        mesa-utils \
    && wget https://d1uj6qtbmh3dt5.cloudfront.net/NICE-GPG-KEY \
    && gpg --import NICE-GPG-KEY \
    && wget https://d1uj6qtbmh3dt5.cloudfront.net/2023.1/Servers/nice-dcv-2023.1-16388-ubuntu2204-x86_64.tgz \
    && tar -xvzf nice-dcv-2023.1-16388-ubuntu2204-x86_64.tgz \
    && cd nice-dcv-2023.1-16388-ubuntu2204-x86_64 \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y \
        ./nice-dcv-server_2023.1.16388-1_amd64.ubuntu2204.deb \
        ./nice-dcv-web-viewer_2023.1.16388-1_amd64.ubuntu2204.deb \
        ./nice-xdcv_2023.1.565-1_amd64.ubuntu2204.deb \
        ./nice-dcv-gl_2023.1.1047-1_amd64.ubuntu2204.deb \
    && rm -rf nice-dcv-2023.1-16388-ubuntu2204-x86_64.tgz \
    && rm -rf nice-dcv-2023.1-16388-ubuntu2204-x86_64

RUN usermod -aG video dcv
# RUN systemctl isolate multi-user.target
# RUN systemctl isolate graphical.target
# RUN dcvgladmin enable
# RUN dcvgldiag

# Install AWS CLI
RUN mkdir -p /tmp/awscli-install \
    && cd /tmp/awscli-install \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf /tmp/awscli-install

# Install Foxbox
RUN wget https://github.com/bmw-software-engineering/foxbox/releases/download/1.0.0/foxbox-1.0.0-linux-amd64.deb \
    && apt-get install -y ./foxbox-1.0.0-linux-amd64.deb \
    && rm -f ./foxbox-1.0.0-linux-amd64.deb

# # Install NVIDIA
# RUN apt install -y apt-utils pkg-config dconf-editor apt-utils gcc xserver-xorg-video-nvidia-535
# RUN apt-get -y install cuda-toolkit-11-4

# RUN wget -q http://us.download.nvidia.com/tesla/535.161/NVIDIA-Linux-x86_64-535.161.08.run -O /tmp/NVIDIA-installer.run \
#  && bash /tmp/NVIDIA-installer.run --accept-license \
#                               --no-runlevel-check \
#                               --no-questions \
#                               --no-backup \
#                               --ui=none \
#                               --no-kernel-module \
#                               --no-nouveau-check \
#                               --install-libglvnd \
#                               --no-nvidia-modprobe \
#                               --no-kernel-module-source \
#  && rm -f /tmp/NVIDIA-installer.run

# RUN apt-cache search nvidia | grep -P '^nvidia-(driver-)?[0-9]+\s' 

#RUN touch /etc/modprobe.d/nvidia.conf
#RUN echo "options nvidia NVreg_EnableGpuFirmware=0" | tee --append /etc/modprobe.d/nvidia.conf
#RUN rm -rf /etc/X11/XF86Config* || true

# Install Python dependencies
RUN pip3 install kubernetes urllib3==1.26.6 boto3

### Configuration Files ###
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
COPY xorg.conf  /etc/X11/xorg.conf
COPY update_parameters.py /opt/dcv_server/scripts
COPY Sample_Nuscenes.json /

#RUN mkdir -p /opt/dcv_server/scripts

# Fix permissions
RUN chmod +x "/usr/local/bin/run_script.sh" \
             "/usr/local/bin/startup_script.sh" \
             "/usr/local/bin/init_session.sh" \
             "/usr/local/bin/check_healthy.sh"

# Expose DCV server port
EXPOSE 8443

CMD ["/usr/local/bin/run_script.sh"]
