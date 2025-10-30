FROM python:3.10-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONBUFFERED=1 

WORKDIR /vegapunk-app

RUN apt-get update && apt-get install -y \
    gcc \
    libpython3-dev \
    && apt-get clean

COPY source/. .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENTRYPOINT [ "python", "main.py" ]