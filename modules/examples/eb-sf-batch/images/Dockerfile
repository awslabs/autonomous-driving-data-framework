FROM python:3.8.13-slim-buster as base

COPY requirements.txt .
RUN pip install -r /requirements.txt

COPY src.py .

CMD ["python","./src.py"]