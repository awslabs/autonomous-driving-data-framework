#!/bin/bash

pip install -r requirements.txt
### Need to use python3.8 specifically
apt update -y
add-apt-repository ppa:deadsnakes/ppa -y
apt install python3.8 -y
apt install python3.8-distutils -y
wget https://bootstrap.pypa.io/get-pip.py
python3.8 get-pip.py
###  install-yq:
export YQ_VERSION=v4.26.1
wget https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_amd64.tar.gz 
tar xvf yq_linux_amd64.tar.gz
mv yq_linux_amd64 /usr/local/bin/yq
rm install-man-page.sh
rm yq.1
yq --version
####  Install kustomize
wget https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize/v3.2.1/kustomize_kustomize.v3.2.1_linux_amd64
chmod +x kustomize_kustomize.v3.2.1_linux_amd64
mv kustomize_kustomize.v3.2.1_linux_amd64 /usr/local/bin/kustomize
kustomize version