# Stage 1: Build
FROM python:3.11-slim AS builder
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set up working directory
WORKDIR /app

# Copy only necessary project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install dependencies into a virtual environment (no project install since package = false)
RUN uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# Install runtime dependencies
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

# Copy the virtual environment and application from builder
COPY --chown=nonroot:nonroot --from=builder /app/.venv/ /app/.venv/
COPY --chown=nonroot:nonroot --from=builder /app/src/ ./src/

# Set environment variables
ENV PYTHONPATH="/app" \
    PATH="/app/.venv/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/sbin:/bin"

EXPOSE 8008
