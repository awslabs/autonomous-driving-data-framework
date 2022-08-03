FROM ros:noetic-perception-focal

# install ros package
RUN apt-get update && apt-get install -y \
      ros-${ROS_DISTRO}-ros-tutorials \
      ros-${ROS_DISTRO}-sensor-msgs \
      ros-${ROS_DISTRO}-common-tutorials && \
    rm -rf /var/lib/apt/lists/*
RUN apt-get update -y 
# RUN apt-get install -y software-properties-common ffmpeg
# RUN add-apt-repository -y ppa:deadsnakes/ppa 
RUN apt-get install -y python3-pip python-is-python3 ffmpeg

WORKDIR /app
RUN python --version
COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY main.py .
COPY entrypoint.sh .
RUN which python
ENV PYTHONPATH="/usr/bin/python"
CMD ["bash"]
