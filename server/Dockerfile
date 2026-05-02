# syntax=docker/dockerfile:1.6
# Dev-friendly image for the FastAPI backend. Compose mounts src/ over this
# layer for hot reload, so what we install here is only the dep tree.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Build deps for cryptography (pyjwt[crypto]) and any future native wheels.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libffi-dev \
 && rm -rf /var/lib/apt/lists/*

# Install dependencies first so they cache when only src/ changes.
COPY pyproject.toml ./
COPY src ./src
RUN pip install -e ".[dev]"

# YAML data lives at the repo root; compose mounts it at /data so the
# repository's `Path(__file__).parents[4] / "data"` resolution finds it.
EXPOSE 8000

CMD ["uvicorn", "agora.interfaces.api.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--reload", "--reload-dir", "/app/src", "--reload-dir", "/data"]
