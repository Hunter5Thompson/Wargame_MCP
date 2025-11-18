# Multi-stage build for optimized production image
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency files
WORKDIR /app
COPY pyproject.toml ./

# Install dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e .

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    CHROMA_PATH=/data/chroma \
    CHROMA_COLLECTION=wargame_docs

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create non-root user
RUN useradd -m -u 1000 wargame && \
    mkdir -p /data/chroma /app && \
    chown -R wargame:wargame /data /app

# Copy application code
WORKDIR /app
COPY --chown=wargame:wargame . .

# Install the package in editable mode
RUN pip install -e .

# Switch to non-root user
USER wargame

# Create data directory
VOLUME ["/data"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from wargame_mcp.mcp_tools import health_check_status; import sys; sys.exit(0 if health_check_status().get('status') == 'ok' else 1)" || exit 1

# Default command
CMD ["wargame-mcp", "health-check"]
