# Stage 1: Build
FROM python:3.11-slim AS builder

# Set environment variables for Poetry
ENV POETRY_VERSION=1.7.2 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies and Poetry
RUN apt-get update && apt-get install -y --no-install-recommends curl build-essential && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    apt-get purge -y --auto-remove curl && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only Poetry files to leverage Docker cache
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --no-dev --no-interaction --no-ansi

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# Create non-privileged user and setup the environment
RUN useradd -m nonroot && \
    mkdir /app && chown nonroot:nonroot /app && \
    mkdir /images && chown nonroot:nonroot /images

USER nonroot
WORKDIR /app

# Copy the application code
COPY --chown=nonroot:nonroot src/ ./src/

# Copy installed dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11

# Expose application port
EXPOSE 8008
