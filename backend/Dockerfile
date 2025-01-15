# Stage 1: Build
FROM python:3.11-slim AS builder
ENV POETRY_VERSION=2.0.1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    mv /root/.local/bin/poetry /usr/local/bin/poetry

# Set up working directory
WORKDIR /app

# Copy only necessary project files
COPY pyproject.toml poetry.lock ./
COPY src/search.py ./src/
COPY src/includes/ ./src/includes/

# Install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# Install runtime dependencies and tree
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgcc1 \
    tree \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m nonroot && \
    mkdir -p /app /images && \
    chown -R nonroot:nonroot /app /images

# Switch to non-root user
USER nonroot
WORKDIR /app

# Copy Python packages and application
COPY --chown=nonroot:nonroot --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --chown=nonroot:nonroot --from=builder /app/src/ ./src/

# Set environment variables
ENV PYTHONPATH="/app" \
    PATH="/usr/local/bin:/usr/local/sbin:/usr/bin:/sbin:/bin"

EXPOSE 8008