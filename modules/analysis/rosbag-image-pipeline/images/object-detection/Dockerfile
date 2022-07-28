# SageMaker PyTorch image - https://github.com/aws/deep-learning-containers/blob/master/available_images.md
ARG BASE_IMAGE
FROM $BASE_IMAGE
#FROM 763104351884.dkr.ecr.eu-central-1.amazonaws.com/pytorch-inference-neuron:1.10.2-neuron-py37-sdk1.19.0-ubuntu18.04

COPY requirements.txt /opt/program/requirements.txt
RUN pip3 install -r /opt/program/requirements.txt
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
ENTRYPOINT ["python3", "detect_objects.py"]