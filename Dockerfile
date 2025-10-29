# CloudClearingAPI Production Dockerfile
# Multi-stage build for optimized image size (<500MB target)
# Version: 2.9.1 (CCAPI-28.0)

# ============================================================================
# Stage 1: Builder - Install dependencies and compile wheels
# ============================================================================
FROM python:3.10-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libspatialindex-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only requirements first for layer caching
COPY requirements-prod.txt /tmp/requirements-prod.txt

# Upgrade pip and install Python dependencies
# Install numpy first to avoid compilation issues with other packages
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir numpy>=1.24.0 && \
    pip install --no-cache-dir -r /tmp/requirements-prod.txt && \
    pip list > /tmp/installed-packages.txt

# ============================================================================
# Stage 2: Runtime - Minimal production image
# ============================================================================
FROM python:3.10-slim

# Metadata
LABEL maintainer="CloudClearingAPI"
LABEL version="2.9.1"
LABEL description="Satellite-based land investment intelligence platform"

# Install runtime dependencies only (not -dev packages for smaller image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal36 \
    libgeos-c1t64 \
    libgeos3.13.1 \
    libproj25 \
    libspatialindex-c8 \
    libspatialindex8 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    # Google Earth Engine
    EARTHENGINE_PROJECT="" \
    GOOGLE_APPLICATION_CREDENTIALS="/app/credentials/gee-service-account.json" \
    # Application settings
    CONFIG_PATH="/app/config/config.yaml" \
    CACHE_DIR="/app/cache" \
    OUTPUT_DIR="/app/output" \
    LOG_LEVEL="INFO"

# Create application user (non-root for security)
RUN useradd -m -u 1000 cloudclearing && \
    mkdir -p /app /app/cache /app/output /app/logs /app/config /app/credentials && \
    chown -R cloudclearing:cloudclearing /app

# Switch to application user
USER cloudclearing
WORKDIR /app

# Copy application code
COPY --chown=cloudclearing:cloudclearing src/ /app/src/
COPY --chown=cloudclearing:cloudclearing run_weekly_java_monitor.py /app/
COPY --chown=cloudclearing:cloudclearing generate_pdf_from_json.py /app/
COPY --chown=cloudclearing:cloudclearing config/ /app/config/

# Copy entrypoint script
COPY --chown=cloudclearing:cloudclearing docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create volume mount points
VOLUME ["/app/cache", "/app/output", "/app/logs", "/app/credentials"]

# Health check (validate Python environment)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import ee; import src.core.automated_monitor; print('OK')" || exit 1

# Expose port for future API (optional)
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command: run weekly monitoring
CMD ["python", "run_weekly_java_monitor.py"]