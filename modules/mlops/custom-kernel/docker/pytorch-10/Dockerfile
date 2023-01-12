FROM continuumio/miniconda3:4.9.2
RUN apt-get --allow-releaseinfo-change update \
&& apt-get install -y ffmpeg \
   --no-install-recommends \
&& rm -rf /var/lib/apt/lists/*
COPY environment.yml .
RUN conda env create -f environment.yml
