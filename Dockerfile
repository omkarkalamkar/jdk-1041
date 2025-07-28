
ARG BUILD_IMAGE="artefact.skao.int/ska-build-python:0.1.1"
ARG BASE_IMAGE="artefact.skao.int/ska-tango-images-tango-python:0.3.0"

# Build stage
FROM $BUILD_IMAGE AS builder

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PATH="/root/.local/bin:$PATH"

# 1. Install ALL dependencies (including test packages)
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-cache && \
    poetry export --format requirements.txt --output requirements.txt --without-hashes --dev

# 2. Copy and install application
COPY . .
RUN poetry install --no-cache

# Runtime stage
FROM $BASE_IMAGE

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Copy virtual environment and requirements
COPY --from=builder /app/.venv .venv
COPY --from=builder /app/requirements.txt .
COPY --from=builder /app/src ./src
COPY --from=builder /app/tests ./tests

# System configuration
USER root
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    chown -R tango:tango /app && \
    find /app -type d -exec chmod 755 {} \; && \
    find /app -type f -exec chmod 644 {} \; && \
    chmod 755 /app/.venv/bin/*

# Tango-specific setup
USER tango