FROM nvcr.io/nvidia/pytorch:21.10-py3

ENV DEBIAN_FRONTEND noninteractive

RUN rm -rf /var/lib/apt/lists/* &&  rm -rf /etc/apt/sources.list.d/*\
    /etc/apt/sources.list.d/cuda.list \
    /etc/apt/sources.list.d/nvidia-ml.list && \
    sed -i s@/archive.ubuntu.com/@/mirrors.ustc.edu.cn/@g /etc/apt/sources.list && \
    apt-get update && apt-get install -y ffmpeg libsm6 libxext6 git ninja-build libglib2.0-0 libsm6 libxrender-dev libxext6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install LaneDet 
RUN conda clean --all
RUN git clone https://github.com/turoad/lanedet.git /lanedet

WORKDIR /lanedet
RUN pip install --no-cache-dir -r requirements.txt  && \
    pip install --no-cache-dir -e .

RUN pip install boto3 awscli
RUN pip install opencv-python==4.5.5.64

RUN mkdir /lanedet/models

RUN wget -O models/laneatt_r34_tusimple.zip --no-check-certificate \
    https://github.com/Turoad/lanedet/releases/download/1.0/laneatt_r34_tusimple.zip

WORKDIR /lanedet/models
RUN unzip laneatt_r34_tusimple.zip
RUN rm -rf ssd/ laneatt_r34_tusimple.zip
COPY detect_lanes.py /lanedet/tools

WORKDIR /lanedet
ENTRYPOINT ["python3", "tools/detect_lanes.py"]
