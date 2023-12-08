# We need to use the nvcr.io/nvidia/pytorch image as a base image to support both linux/amd64 and linux_arm64 platforms.
# PyTorch=1.13.0, cuda=11.8.0
# Ref: https://github.com/kubeflow/katib/tree/master/examples/v1beta1/trial-images/pytorch-mnist
FROM 763104351884.dkr.ecr.eu-central-1.amazonaws.com/pytorch-training:2.1.0-gpu-py310-cu121-ubuntu20.04-ec2

ADD . /aws/pytorch-mnist

WORKDIR /aws/pytorch-mnist

# Add folder for the logs.
RUN mkdir /ml


RUN chgrp -R 0 /aws/pytorch-mnist \
  && chmod -R g+rwX /aws/pytorch-mnist \
  && chgrp -R 0 /ml \
  && chmod -R g+rwX /ml

RUN pip install cloudml-hypertune
RUN pip install boto3


ENTRYPOINT ["python3", "/aws/pytorch-mnist/mnist.py"]