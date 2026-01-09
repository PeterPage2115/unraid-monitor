# =============================================================================
# Unraid Monitor - Docker Image
# =============================================================================
# Multi-stage build for smaller final image
# Base: Python 3.12 Alpine (smaller, fewer vulnerabilities)
# =============================================================================

FROM python:3.12-alpine AS builder

# Install build dependencies
RUN apk add --no-cache gcc musl-dev linux-headers

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# =============================================================================
# Final image
# =============================================================================

FROM python:3.12-alpine

# Labels
LABEL maintainer="Unraid Monitor"
LABEL description="Discord monitoring bot for Unraid servers"
LABEL version="1.0.0"

# Create non-root user
RUN adduser -D -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appuser src/ ./src/

# Copy default config
COPY --chown=appuser:appuser config/settings.yaml ./config/settings.yaml

# Create directories for config and data
RUN mkdir -p /app/data && \
    chown -R appuser:appuser /app/data

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src
ENV HOST_PROC=/host/proc
ENV HOST_SYS=/host/sys
ENV TZ=Europe/Warsaw

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Working directory for running
WORKDIR /app/src

# Run the application
CMD ["python", "-u", "main.py"]
