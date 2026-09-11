# apps/backend/app/core/metrics.py
"""
Production metrics infrastructure for Lumenly Backend.

Implements Prometheus-compatible metrics for:
- HTTP requests (count, latency, in-flight)
- Authentication (login attempts, successes, failures)
- Security (authorization failures, cross-tenant attempts, rate limits)
- Database health (PostgreSQL, MongoDB, Redis, Qdrant)
- Celery tasks (executions, failures, retries, duration)
- LLM requests (count, failures, duration, token usage)
- WebSocket (connections, failures, messages)
- Document processing (success, failures, duration)
- Rate limiting (violations)

All metrics follow low-cardinality principles and never expose sensitive data.
"""

import os

# Enable multiprocess mode for Uvicorn workers
# This is required when using --workers > 1 in Uvicorn
# IMPORTANT: This must be set BEFORE importing prometheus_client
if "PROMETHEUS_MULTIPROC_DIR" not in os.environ:
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = "/tmp/prometheus_multiproc"

# Ensure the directory exists for multiprocess metrics files
try:
    os.makedirs(os.environ["PROMETHEUS_MULTIPROC_DIR"], exist_ok=True)
except Exception:
    # If directory creation fails, continue anyway - tests may handle this
    pass

from prometheus_client import Counter, Gauge, Histogram

# =============================================================================
# HTTP METRICS
# =============================================================================

http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "route", "status_code"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "route", "status_code"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
        float("inf"),
    ),
)

http_requests_in_flight = Gauge(
    "http_requests_in_flight", "Number of HTTP requests currently in flight", ["method"]
)

# =============================================================================
# AUTHENTICATION METRICS
# =============================================================================

auth_login_attempts_total = Counter(
    "auth_login_attempts_total", "Total authentication login attempts", ["result"]
)

auth_token_refresh_total = Counter(
    "auth_token_refresh_total", "Total authentication token refresh attempts", ["result"]
)

auth_registration_attempts_total = Counter(
    "auth_registration_attempts_total", "Total user registration attempts", ["result"]
)

# =============================================================================
# SECURITY METRICS
# =============================================================================

security_authorization_failures_total = Counter(
    "security_authorization_failures_total", "Total authorization failures", ["resource_type"]
)

security_cross_tenant_attempts_total = Counter(
    "security_cross_tenant_attempts_total", "Total cross-tenant access attempts", ["resource_type"]
)

security_rate_limit_exceeded_total = Counter(
    "security_rate_limit_exceeded_total", "Total rate limit violations", ["endpoint", "user_role"]
)

# =============================================================================
# DATABASE HEALTH METRICS
# =============================================================================

database_health_status = Gauge(
    "database_health_status", "Database health status (1=healthy, 0=unhealthy)", ["database"]
)

database_operation_failures_total = Counter(
    "database_operation_failures_total",
    "Total database operation failures",
    ["database", "operation_type"],
)

# =============================================================================
# CELERY METRICS
# =============================================================================

celery_tasks_total = Counter(
    "celery_tasks_total", "Total Celery task executions", ["task", "status"]
)

celery_task_failures_total = Counter(
    "celery_task_failures_total", "Total Celery task failures", ["task", "failure_type"]
)

celery_task_retries_total = Counter(
    "celery_task_retries_total", "Total Celery task retries", ["task"]
)

celery_task_duration_seconds = Histogram(
    "celery_task_duration_seconds",
    "Celery task execution duration in seconds",
    ["task"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, float("inf")),
)

# =============================================================================
# LLM METRICS
# =============================================================================

llm_requests_total = Counter("llm_requests_total", "Total LLM API requests", ["provider", "model"])

llm_request_failures_total = Counter(
    "llm_request_failures_total", "Total LLM API request failures", ["provider", "failure_type"]
)

llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM request duration in seconds",
    ["provider"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float("inf")),
)

llm_input_tokens_total = Counter(
    "llm_input_tokens_total", "Total LLM input tokens consumed", ["provider"]
)

llm_output_tokens_total = Counter(
    "llm_output_tokens_total", "Total LLM output tokens consumed", ["provider"]
)

# =============================================================================
# WEBSOCKET METRICS
# =============================================================================

websocket_connections_total = Counter(
    "websocket_connections_total", "Total WebSocket connection attempts", ["result"]
)

websocket_disconnects_total = Counter(
    "websocket_disconnects_total", "Total WebSocket disconnections", ["reason"]
)

websocket_messages_total = Counter(
    "websocket_messages_total", "Total WebSocket messages processed", ["message_type", "direction"]
)

websocket_message_failures_total = Counter(
    "websocket_message_failures_total",
    "Total WebSocket message processing failures",
    ["failure_type"],
)

websocket_active_connections = Gauge(
    "websocket_active_connections", "Number of currently active WebSocket connections"
)

# =============================================================================
# DOCUMENT PROCESSING METRICS
# =============================================================================

document_processing_total = Counter(
    "document_processing_total", "Total document processing attempts", ["status"]
)

document_processing_duration_seconds = Histogram(
    "document_processing_duration_seconds",
    "Document processing duration in seconds",
    ["status"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0, float("inf")),
)

vector_ingestion_failures_total = Counter(
    "vector_ingestion_failures_total", "Total vector ingestion failures", ["failure_type"]
)

# =============================================================================
# RATE LIMIT METRICS
# =============================================================================

rate_limit_violations_total = Counter(
    "rate_limit_violations_total", "Total rate limit violations", ["limit_type", "user_role"]
)

# =============================================================================
# METRICS INITIALIZATION
# =============================================================================


def initialize_metrics():
    """
    Initialize metrics and set default values.

    This should be called during application startup to ensure
    all metrics are registered and have sensible default values.
    """
    # Initialize database health metrics to unhealthy (0)
    # They will be updated to healthy (1) by health checks
    database_health_status.labels(database="postgresql").set(0)
    database_health_status.labels(database="mongodb").set(0)
    database_health_status.labels(database="redis").set(0)
    database_health_status.labels(database="qdrant").set(0)

    # Initialize WebSocket active connections to 0
    websocket_active_connections.set(0)

    # Initialize HTTP in-flight metrics to 0
    http_requests_in_flight.labels(method="GET").set(0)
    http_requests_in_flight.labels(method="POST").set(0)
    http_requests_in_flight.labels(method="PUT").set(0)
    http_requests_in_flight.labels(method="DELETE").set(0)
    http_requests_in_flight.labels(method="PATCH").set(0)
    http_requests_in_flight.labels(method="OPTIONS").set(0)
    http_requests_in_flight.labels(method="HEAD").set(0)
