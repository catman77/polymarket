# Polymarket AutoTrader - Production Dockerfile
# 
# Multi-stage build for optimized image size and security
# 
# Build: docker build -t polymarket-bot:latest -f docker/Dockerfile .
# Run: docker run --env-file .env polymarket-bot:latest

# =============================================================================
# Stage 1: Builder - Install dependencies and compile
# =============================================================================
FROM python:3.11-slim AS builder

# Set build-time environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip wheel setuptools && \
    pip install -r requirements.txt

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:3.11-slim AS runtime

# Security: Run as non-root user
RUN groupadd -r botuser && useradd -r -g botuser botuser

# Set runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=botuser:botuser . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/state /app/logs /app/simulation && \
    chown -R botuser:botuser /app/state /app/logs /app/simulation

# Security: Remove write access to code
RUN chmod -R a-w /app/*.py /app/bot /app/agents /app/coordinator /app/config

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('https://data-api.polymarket.com', timeout=5)" || exit 1

# Switch to non-root user
USER botuser

# Default command - run the bot
CMD ["python", "bot/momentum_bot_v12.py"]

# =============================================================================
# Labels for image metadata
# =============================================================================
LABEL org.opencontainers.image.title="Polymarket AutoTrader" \
      org.opencontainers.image.description="Automated trading bot for Polymarket prediction markets" \
      org.opencontainers.image.version="12.1" \
      org.opencontainers.image.authors="Development Team" \
      org.opencontainers.image.source="https://github.com/user/polymarket-autotrader"
