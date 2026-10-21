FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/data/runtime-models/huggingface

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt requirements-model.txt ./
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt

COPY config.py ./config.py
COPY src ./src

RUN useradd --create-home --uid 10001 suriph && \
    mkdir -p /app/data/runtime-sqlite /app/data/runtime-media /app/data/runtime-models && \
    mkdir -p /app/models && chown -R suriph:suriph /app/data /app/models

USER suriph
EXPOSE 8000
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-access-log"]
