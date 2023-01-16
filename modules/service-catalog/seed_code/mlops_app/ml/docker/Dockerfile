FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-training:1.12.1-gpu-py38-ubuntu20.04-sagemaker

USER root

## Add custom dependencies
RUN apt-get --allow-releaseinfo-change update \
&& apt-get install -y build-essential ffmpeg gcc  \
    --no-install-recommends \
&& rm -rf /var/lib/apt/lists/*
