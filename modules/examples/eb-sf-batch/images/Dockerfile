FROM public.ecr.aws/docker/library/python:3.10-slim-buster as base

COPY requirements.txt .
RUN pip install -r /requirements.txt

COPY src.py .

RUN useradd -m -u 3141 appuser && chown appuser:appuser requirements.txt src.py
USER appuser

CMD ["python","./src.py"]