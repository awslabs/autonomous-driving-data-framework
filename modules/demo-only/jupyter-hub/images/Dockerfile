FROM jupyterhub/k8s-singleuser-sample:1.2.0

USER root

RUN apt-get update && apt-get install -yq --no-install-recommends \
    curl \
    zip \
    unzip \
    vim

RUN pip install awscli pandas graph-notebook 
RUN echo 'jovyan ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER jovyan

CMD ["bash"]