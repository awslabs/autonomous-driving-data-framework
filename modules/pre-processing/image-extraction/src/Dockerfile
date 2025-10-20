FROM nvcr.io/nvidia/tensorflow:22.05-tf1-py3

RUN apt update && apt upgrade -y && \
    apt install git python3-pip yasm pkg-config libvpx-dev s3fs awscli -y && \
    rm -rf /var/lib/apt/lists/*

# Install Mountpoint for Amazon S3: https://github.com/awslabs/mountpoint-s3/blob/main/doc/INSTALL.md
RUN wget https://s3.amazonaws.com/mountpoint-s3-release/latest/x86_64/mount-s3.deb
RUN apt-get install -y ./mount-s3.deb

ADD entrypoint.sh /opt/entrypoint.sh

ADD extract_images_from_jseq.py /opt/extract_images_from_jseq.py
RUN chmod +x /opt/entrypoint.sh

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /opt
USER appuser

ENTRYPOINT ["/opt/entrypoint.sh"]

