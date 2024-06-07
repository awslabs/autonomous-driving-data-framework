FROM ubuntu:22.04 as dcv

USER root

ARG DEBIAN_FRONTEND=noninteractive

# Prepare the container to run systemd inside
ENV container docker
ENV NVIDIA_DRIVER_CAPABILITIES compute,graphics,utility

# Install tools
RUN apt-get update  && apt upgrade -y &&\
	apt-get install -y \
		tar vim wget kmod software-properties-common apt-transport-https \
		sudo pciutils ca-certificates xz-utils locales curl zip s3fs fuse tar && \
		apt-get update

RUN apt-get install -y snap snapd
RUN apt-get -yq install tar
RUN cd /tmp && wget https://s3.amazonaws.com/mountpoint-s3-release/latest/x86_64/mount-s3.deb && apt-get install ./mount-s3.deb && rm mount-s3.deb

RUN apt-get update && apt-get install -y python3-pip

RUN pip3 install gpustat

RUN apt-get install -y gcc g++
RUN apt-get install -y libvulkan-dev libxext6 libvulkan1 vulkan-tools

## Install Vulkan SDK
RUN wget -qO- https://packages.lunarg.com/lunarg-signing-key-pub.asc | tee /etc/apt/trusted.gpg.d/lunarg.asc && \
    wget -qO /etc/apt/sources.list.d/lunarg-vulkan-jammy.list http://packages.lunarg.com/vulkan/lunarg-vulkan-jammy.list && \
    apt-get update -y && \
    apt-get install -y vulkan-sdk

RUN apt-get install -y libwebsocketpp-dev nlohmann-json3-dev openssh-server xvfb jq
RUN /etc/init.d/ssh start

COPY nvidia_icd.json /usr/share/vulkan/icd.d

# Install ros2
# Setup the sources
ENV ROS_VERSION=2
ENV ROS_DISTRO=humble
ENV ROS_PYTHON_VERSION=3
RUN apt-get install -y libasio-dev
RUN apt-get update && apt-get install -y software-properties-common curl && \
    add-apt-repository universe && \
    curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | tee /etc/apt/sources.list.d/ros2.list > /dev/null
    # Install ROS 2 packages
    RUN apt-get update && apt-get upgrade -y && \
        apt-get install -y ros-humble-desktop

# install bootstrap tools
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    git \
    nano \
    iputils-ping \
    wget \
    python3-colcon-common-extensions \
    python3-colcon-mixin \
    python3-rosdep \
    python3-vcstool \
    && rm -rf /var/lib/apt/lists/*

# bootstrap rosdep
RUN rosdep init && \
  rosdep update --rosdistro humble

# Environment setup
RUN echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc

COPY eureka_controller.sh /usr/local/bin
COPY check_healthy.sh /usr/local/bin
COPY eureka_worker.sh /usr/local/bin
COPY conda_setup.sh /usr/local/bin

RUN chmod +x "/usr/local/bin/eureka_controller.sh" \
             "/usr/local/bin/check_healthy.sh" \
             "/usr/local/bin/eureka_worker.sh" \
             "/usr/local/bin/conda_setup.sh"

CMD ["/bin/bash", "/usr/local/bin/conda_setup.sh"]
