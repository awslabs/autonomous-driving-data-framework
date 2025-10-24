FROM python:3.8.13-slim-buster as base

COPY src/requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

RUN mkdir -p /var/simulation-mock
ADD src /var/simulation-mock/

RUN cd /var/simulation-mock/ && \
    pip3 install -e .

WORKDIR /var/simulation-mock/

RUN useradd -m -u 3141 appuser && chown -R appuser:appuser /var/simulation-mock
USER appuser

CMD ["bash"]
