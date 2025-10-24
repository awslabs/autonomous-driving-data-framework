FROM python:3.8.13-slim-buster as base

COPY requirements.txt .
RUN pip install -r /requirements.txt

COPY src.py .

RUN useradd -m -u 3141 appuser && chown appuser:appuser requirements.txt src.py
USER appuser

CMD ["python","./src.py"]