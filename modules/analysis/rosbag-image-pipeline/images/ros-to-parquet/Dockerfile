FROM python:3.7.13-slim-buster

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get -qq install gcc

RUN mkdir /app
COPY requirements.txt /requirements.txt
RUN pip install numba
RUN pip install -r requirements.txt

COPY app /app
WORKDIR /app

CMD ["bash"]
