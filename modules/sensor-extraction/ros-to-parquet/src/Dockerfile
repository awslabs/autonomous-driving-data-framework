FROM public.ecr.aws/docker/library/python:3.7.13-slim-buster

RUN sed -i 's/deb.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    sed -i '/stretch-updates/d' /etc/apt/sources.list

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get -qq install gcc

RUN mkdir /app
COPY requirements.txt /requirements.txt
RUN pip install numba
RUN pip install -r requirements.txt

COPY main.py /app/main.py
COPY entrypoint.sh /app/entrypoint.sh
WORKDIR /app

RUN useradd -m -u 3141 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["bash"]
