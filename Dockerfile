FROM python:3.13-slim

RUN apt-get update \
    && apt-get install git ffmpeg -y  \
    && apt-get clean  \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    uv pip install --system --no-cache-dir -r requirements.txt \
    && uv pip install --system torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu126

COPY ./mUSh ./mUSh

CMD ["python", "-m", "mUSh"]
