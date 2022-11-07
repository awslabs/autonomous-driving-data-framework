FROM public.ecr.aws/docker/library/python:3.7.13-slim-buster
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

CMD ["bash"]
