# SageMaker PyTorch image - https://github.com/aws/deep-learning-containers/blob/master/available_images.md
FROM 763104351884.dkr.ecr.eu-central-1.amazonaws.com/pytorch-training:1.5.1-cpu-py36-ubuntu16.04
#FROM 763104351884.dkr.ecr.eu-central-1.amazonaws.com/pytorch-inference-neuron:1.10.2-neuron-py37-sdk1.19.0-ubuntu18.04

RUN apt-get -y update && apt-get install -y --no-install-recommends \
         wget \
         nginx \
         ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /opt/program/requirements.txt
RUN pip3 install --no-cache-dir -r /opt/program/requirements.txt
RUN pip3 install boto3
# Set some environment variables. PYTHONUNBUFFERED keeps Python from buffering our standard
# output stream, which means that logs can be delivered to the user quickly. PYTHONDONTWRITEBYTECODE
# keeps Python from writing the .pyc files which are unnecessary in this case. We also update
# PATH so that the train and serve programs are found when the container is invoked.

ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PATH="/opt/program:${PATH}"
ENV MODEL_PATH="/opt/ml/model"

# Set up the program in the image
COPY algorithm_code /opt/program
WORKDIR /opt/program
# /opt/ml and all subdirectories are utilized by SageMaker, use the /code subdirectory to store your user code.
ENTRYPOINT ["python3", "detect_lanes.py"]