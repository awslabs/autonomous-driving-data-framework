#FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:1.10.2-cpu-py38-ubuntu20.04-e3
ARG BASE_IMAGE
FROM $BASE_IMAGE

ENV DEBIAN_FRONTEND noninteractive
RUN conda clean --all
RUN git clone https://github.com/hustvl/YOLOP.git /YOLOP

WORKDIR /YOLOP
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install boto3 awscli

COPY detect_lanes.py tools/detect_lanes.py

WORKDIR /YOLOP
ENTRYPOINT ["python3", "tools/detect_lanes.py"]
