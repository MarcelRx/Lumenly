# Multi-stage production Dockerfile for Lumenly Backend
# Stage 1: Builder
FROM python:3.11-slim as builder

# Set build arguments
ARG APP_VERSION=0.1.0
ARG APP_NAME=lumenly-backend

# Set environment variables for build
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies to a temporary location
RUN pip install --user --prefix=/install requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim as runtime

# Set runtime arguments
ARG APP_VERSION=0.1.0
ARG APP_NAME=lumenly-backend
ARG APP_USER=lumenly
ARG APP_UID=1000
ARG APP_GID=1000

# Set environment variables for runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_VERSION=${APP_VERSION} \
    APP_NAME=${APP_NAME} \
    PATH=/install/bin:$PATH

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and group
RUN groupadd -g ${APP_GID} ${APP_USER} && \
    useradd -u ${APP_UID} -g ${APP_GID} -m -s /bin/bash ${APP_USER}

# Copy installed Python packages from builder
COPY --from=builder /install /install

# Create app directory with correct permissions
WORKDIR /app
RUN chown -R ${APP_USER}:${APP_USER} /app

# Copy application code
COPY --chown=${APP_USER}:${APP_USER} app ./app
COPY --chown=${APP_USER}:${APP_USER} alembic.ini .
COPY --chown=${APP_USER}:${APP_USER} alembic ./alembic

# Switch to non-root user
USER ${APP_USER}

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Run the application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-level", "info"]
