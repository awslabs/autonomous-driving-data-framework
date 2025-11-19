FROM public.ecr.aws/docker/library/ros:humble-perception

# install ros package
RUN apt-get update && apt-get install -y \
      ros-${ROS_DISTRO}-demo-nodes-cpp \
      ros-${ROS_DISTRO}-sensor-msgs \
      ros-${ROS_DISTRO}-cv-bridge \
      ros-${ROS_DISTRO}-rosbag2-py \
      ros-${ROS_DISTRO}-rclpy \
      ros-${ROS_DISTRO}-rosidl-runtime-py \
      python3-pip \
      ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY main.py .
COPY entrypoint.sh .

#RUN useradd -m -u 3141 appuser && chown -R appuser:appuser /app
#USER appuser

CMD ["bash"]
