FROM python:3.8.7-slim-buster as base

COPY src/requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

RUN mkdir -p /var/processing-mock
ADD src /var/processing-mock/

RUN cd /var/processing-mock/ && \
    pip3 install -e .

WORKDIR /var/processing-mock/

CMD ["bash"]
