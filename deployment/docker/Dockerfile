# Colosseum CuratorAgent Container Image
FROM python:3.11-slim

LABEL org.opencontainers.image.title="Colosseum CuratorAgent"
LABEL org.opencontainers.image.description="The Keeper of Records for the Colosseum Investment Committee"
LABEL org.opencontainers.image.source="https://github.com/davdunc/colosseum"
LABEL org.opencontainers.image.licenses="MIT"

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        postgresql-client \
        ca-certificates \
        curl \
        && \
    rm -rf /var/lib/apt/lists/*

# Create application user
RUN useradd -r -s /bin/bash -u 1000 colosseum

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY colosseum/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY colosseum/ /app/colosseum/
COPY examples/ /app/examples/

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R colosseum:colosseum /app

# Switch to non-root user
USER colosseum

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -m colosseum.cli.curator health || exit 1

# Default command
CMD ["python", "-m", "colosseum.cli.curator", "start", "--interval", "60"]
