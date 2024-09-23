FROM public.ecr.aws/ubuntu/ubuntu:20.04
USER root

ARG DCV_SM_NAME
ENV DISPLAY=:0 
ARG DEBIAN_FRONTEND=noninteractive
ENV GNOME_SHELL_SESSION_MODE=ubuntu
ENV XDG_CURRENT_DESKTOP=ubuntu:GNOME
ENV XDG_CONFIG_DIRS=/etc/xdg/xdg-ubuntu:/etc/xdg
ENV DCV_SM_NAME=$DCV_SM_NAME
# Prepare the container to run systemd inside
ENV container docker

# Enable Universe repository (to install freeglut-3)
RUN	apt-get update && apt-get install software-properties-common -y &&\
	add-apt-repository universe

# Run apt update & upgrade
RUN apt-get update && apt upgrade -y

# Install tools
RUN apt-get install -y \
	tar vim jq wget kmod software-properties-common apt-transport-https \
	sudo pciutils ca-certificates xz-utils locales curl iputils-ping firewalld && \
	apt-get update

# Install X Server, Gnome and GL libs/dependencies
RUN apt-get install -y \
	mesa-utils libxvmc-dev libxatracker-dev \
	xserver-xorg-core xserver-xorg xserver-xorg-dev xorg x11-utils xauth xinit  \
	openbox  xfonts-base xterm freeglut3 freeglut3-dev ubuntu-desktop-minimal gnome-shell gdm3 \
	libglfw3-dev libgles2-mesa-dev libglew-dev glew-utils

# Install Metacity window manager
RUN apt-get install -y \
	metacity xdotool wmctrl
# Install python dependencies
RUN apt-get install -y python3-pip unzip && \
    pip3 install kubernetes boto3

# Install Nvidia Driver, configure Xorg, install NICE DCV server
ENV NVIDIA_VISIBLE_DEVICES all
# ENV NVIDIA_DRIVER_CAPABILITIES compute,utility
ENV NVIDIA_DRIVER_CAPABILITIES all

# The version should match EKS node's driver version (check the driver version by running `nvidia-smi --query-gpu=driver_version --format=csv,noheader` on the node)
RUN wget -q https://download.nvidia.com/XFree86/Linux-x86_64//535.161.07/NVIDIA-Linux-x86_64-535.161.07.run -O /tmp/NVIDIA-installer.run
RUN bash /tmp/NVIDIA-installer.run --accept-license \
	--install-libglvnd \
	--no-questions --no-kernel-module-source \
	--no-nvidia-modprobe --no-kernel-module \
	--disable-nouveau \
	--no-backup \
	--ui=none \
 && rm -f /tmp/NVIDIA-installer.run \
 && nvidia-xconfig --preserve-busid --enable-all-gpus -connected-monitor=DFP-0,DFP-1,DFP-2,DFP-3

# Install NICE DCV
RUN mkdir -p /tmp/dcv-inst && \
	cd /tmp/dcv-inst && \
	wget https://d1uj6qtbmh3dt5.cloudfront.net/NICE-GPG-KEY && \
	gpg --import NICE-GPG-KEY && \
	wget https://d1uj6qtbmh3dt5.cloudfront.net/2022.2/Servers/nice-dcv-2022.2-13907-ubuntu2004-x86_64.tgz && \
	tar -xvzf nice-dcv-2022.2-13907-ubuntu2004-x86_64.tgz && cd nice-dcv-2022.2-13907-ubuntu2004-x86_64 && \
	apt install -y \
		./nice-dcv-server_2022.2.13907-1_amd64.ubuntu2004.deb  \
		./nice-dcv-web-viewer_2022.2.13907-1_amd64.ubuntu2004.deb \
		./nice-xdcv_2022.2.481-1_amd64.ubuntu2004.deb \
		./nice-dcv-gl_2022.2.983-1_amd64.ubuntu2004.deb  \
		./nice-dcv-simple-external-authenticator_2022.2.198-1_amd64.ubuntu2004.deb -y && \
	usermod -aG video dcv && \
	rm -rf /tmp/dcv-inst



# Create a location for session init and autorun script logs
RUN mkdir -p /var/log/init_session && chmod 777 /var/log/init_session
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


# Configure XFCE to prevent automatic logout
RUN mkdir -p /etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml

# Disable screen saver and power management
COPY xfce4/xfce4-power-manager.xml /etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-power-manager.xml
COPY xfce4/xfce4-screensaver.xml /etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-screensaver.xml

# # Disable the update-motd scripts (Ubuntu welcome / message of the day dialog)
# RUN chmod -x /etc/update-motd.d/*
RUN echo 'ENABLED=0' > /etc/default/motd-news
RUN truncate -s 0 /etc/motd

# Copy GDM3 custom config (disable Wayland - force Xorg, enable debug, auto login etc)
COPY config/gdm3_custom.conf /etc/gdm3/custom.conf
# Copy X11 DRI3 configuration for Nvidia
RUN mkdir -p /etc/X11/xorg.conf.d/
COPY config/dri3-nvidia.conf /etc/X11/xorg.conf.d/10-nvidia.conf

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
RUN chmod a+x "/usr/local/bin/run_script.sh" \
             "/usr/local/bin/startup_script.sh" \
             "/usr/local/bin/init_session.sh" \
             "/usr/local/bin/check_healthy.sh"


# Add ubuntu to sudoers, needed to run window manager within init_session.sh
RUN echo 'ubuntu ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
EXPOSE 8443

CMD ["/usr/local/bin/run_script.sh"]