# syntax=docker/dockerfile:1.6

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONPATH=/app/src \
    PATH=/root/.local/bin:$PATH

WORKDIR /app

# System deps (minimal); add build tools only if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates build-essential python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION}

# Copy dependency manifest first for better Docker layer caching
COPY pyproject.toml poetry.lock* ./

# Install deps (no dev)
RUN poetry install --no-interaction --no-ansi --only main

# Copy source
COPY src ./src
COPY migrations ./migrations
COPY Procfile ./Procfile

EXPOSE 8000

# Default command runs the API; worker is provided as a separate service in compose
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
