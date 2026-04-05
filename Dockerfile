# syntax=docker/dockerfile:1.7

FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

COPY tourin ./tourin
COPY assets ./assets

EXPOSE 5000

CMD ["gunicorn", "tourin.server.api:app", "--bind", "0.0.0.0:5000", "--workers", "1"]
