FROM public.ecr.aws/docker/library/python:3.10-slim-buster

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY app/ /app/

RUN useradd -m -u 3141 appuser && chown -R appuser:appuser /app
USER appuser

CMD [ "python", "-m" , "flask", "run", "--host=0.0.0.0"]