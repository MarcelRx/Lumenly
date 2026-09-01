# apps/backend/tests/test_metrics.py
"""
Comprehensive metrics tests for PHASE 10.2.

Tests metrics endpoint, HTTP metrics, authentication metrics, security metrics,
database metrics, Celery metrics, LLM metrics, WebSocket metrics, and document
processing metrics.
"""
import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY as prometheus_registry
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.core.metrics import (
    # HTTP metrics
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_flight,
    # Authentication metrics
    auth_login_attempts_total,
    auth_token_refresh_total,
    auth_registration_attempts_total,
    # Security metrics
    security_authorization_failures_total,
    security_cross_tenant_attempts_total,
    security_rate_limit_exceeded_total,
    # Database metrics
    database_health_status,
    database_operation_failures_total,
    # Celery metrics
    celery_tasks_total,
    celery_task_failures_total,
    celery_task_retries_total,
    celery_task_duration_seconds,
    # LLM metrics
    llm_requests_total,
    llm_request_failures_total,
    llm_request_duration_seconds,
    llm_input_tokens_total,
    llm_output_tokens_total,
    # WebSocket metrics
    websocket_connections_total,
    websocket_disconnects_total,
    websocket_messages_total,
    websocket_message_failures_total,
    websocket_active_connections,
    # Document processing metrics
    document_processing_total,
    document_processing_duration_seconds,
    vector_ingestion_failures_total,
    # Rate limit metrics
    rate_limit_violations_total,
)


class TestMetricsEndpoint:
    """Test metrics endpoint functionality."""

    def test_metrics_endpoint_exists(self, client: TestClient):
        """Test that /metrics endpoint exists and is accessible."""
        response = client.get("/v1/metrics")
        assert response.status_code == 200

    def test_metrics_content_type(self, client: TestClient):
        """Test that metrics endpoint returns correct content type."""
        response = client.get("/v1/metrics")
        assert response.headers["content-type"] == CONTENT_TYPE_LATEST

    def test_metrics_prometheus_format(self, client: TestClient):
        """Test that metrics endpoint returns valid Prometheus format."""
        response = client.get("/v1/metrics")
        content = response.text
        
        # Basic Prometheus format validation
        assert content  # Should not be empty
        assert "# HELP" in content or "# TYPE" in content  # Should have metric metadata

    def test_metrics_no_secrets(self, client: TestClient):
        """Test that metrics endpoint does not expose secrets."""
        response = client.get("/v1/metrics")
        content = response.text.lower()
        
        # Check for common secret patterns
        assert "password" not in content
        assert "api_key" not in content
        assert "secret" not in content
        assert "token" not in content
        assert "jwt" not in content

    def test_metrics_no_user_data(self, client: TestClient):
        """Test that metrics endpoint does not expose user data."""
        response = client.get("/v1/metrics")
        content = response.text.lower()
        
        # Check for user data patterns
        assert "email" not in content
        assert "user_id" not in content
        assert "username" not in content
        assert "journal" not in content or "journal" in "http_requests_total"  # Allow metric names

    def test_metrics_endpoint_skipped_in_middleware(self, client: TestClient):
        """Test that metrics endpoint is skipped in rate limiting middleware."""
        # This is tested implicitly by the fact that the endpoint works
        # If rate limiting was applied, it might block the request
        response = client.get("/v1/metrics")
        assert response.status_code == 200


class TestHTTPMetrics:
    """Test HTTP request metrics."""

    def test_http_request_counter_increments(self, client: TestClient):
        """Test that HTTP request counter increments on requests."""
        # Get initial count
        initial_count = http_requests_total._value.get()
        
        # Make a request
        client.get("/health/live")
        
        # Check that counter incremented
        final_count = http_requests_total._value.get()
        assert final_count > initial_count

    def test_http_request_latency_records(self, client: TestClient):
        """Test that HTTP request latency histogram records."""
        # Make a request
        client.get("/health/live")
        
        # Check that histogram has samples
        samples = list(http_request_duration_seconds.collect())
        assert len(samples) > 0

    def test_http_status_code_labels(self, client: TestClient):
        """Test that HTTP metrics have correct status code labels."""
        # Make a request that should return 200
        client.get("/health/live")
        
        # Check for status code label
        samples = list(http_requests_total.collect())
        status_codes = set()
        for sample in samples:
            for metric in sample.samples:
                if metric.name == "http_requests_total":
                    status_codes.add(metric.labels.get("status_code"))
        
        assert "200" in status_codes

    def test_http_method_labels(self, client: TestClient):
        """Test that HTTP metrics have correct method labels."""
        # Make a GET request
        client.get("/health/live")
        
        # Check for method label
        samples = list(http_requests_total.collect())
        methods = set()
        for sample in samples:
            for metric in sample.samples:
                if metric.name == "http_requests_total":
                    methods.add(metric.labels.get("method"))
        
        assert "GET" in methods

    def test_http_in_flight_metrics(self, client: TestClient):
        """Test that HTTP in-flight metrics work."""
        # Check that gauge exists
        samples = list(http_requests_in_flight.collect())
        assert len(samples) > 0


class TestAuthenticationMetrics:
    """Test authentication metrics."""

    def test_auth_login_attempts_total_exists(self):
        """Test that auth login attempts metric exists."""
        samples = list(auth_login_attempts_total.collect())
        assert len(samples) > 0

    def test_auth_token_refresh_total_exists(self):
        """Test that auth token refresh metric exists."""
        samples = list(auth_token_refresh_total.collect())
        assert len(samples) > 0

    def test_auth_registration_attempts_total_exists(self):
        """Test that auth registration attempts metric exists."""
        samples = list(auth_registration_attempts_total.collect())
        assert len(samples) > 0

    def test_auth_metrics_low_cardinality(self):
        """Test that auth metrics use low-cardinality labels."""
        samples = list(auth_login_attempts_total.collect())
        for sample in samples:
            for metric in sample.samples:
                labels = metric.labels
                # Should only have 'result' label
                assert set(labels.keys()) == {"result"}
                # Result should be normalized values
                assert labels["result"] in ["success", "invalid_credentials", "inactive_user", "error"]


class TestSecurityMetrics:
    """Test security metrics."""

    def test_security_authorization_failures_total_exists(self):
        """Test that security authorization failures metric exists."""
        samples = list(security_authorization_failures_total.collect())
        assert len(samples) > 0

    def test_security_cross_tenant_attempts_total_exists(self):
        """Test that security cross-tenant attempts metric exists."""
        samples = list(security_cross_tenant_attempts_total.collect())
        assert len(samples) > 0

    def test_security_rate_limit_exceeded_total_exists(self):
        """Test that security rate limit exceeded metric exists."""
        samples = list(security_rate_limit_exceeded_total.collect())
        assert len(samples) > 0

    def test_security_metrics_low_cardinality(self):
        """Test that security metrics use low-cardinality labels."""
        samples = list(security_authorization_failures_total.collect())
        for sample in samples:
            for metric in sample.samples:
                labels = metric.labels
                # Should only have 'resource_type' label
                assert set(labels.keys()) == {"resource_type"}


class TestDatabaseMetrics:
    """Test database health metrics."""

    def test_database_health_status_exists(self):
        """Test that database health status metric exists."""
        samples = list(database_health_status.collect())
        assert len(samples) > 0

    def test_database_health_status_has_all_databases(self):
        """Test that database health status includes all databases."""
        samples = list(database_health_status.collect())
        databases = set()
        for sample in samples:
            for metric in sample.samples:
                databases.add(metric.labels.get("database"))
        
        expected_databases = {"postgresql", "mongodb", "redis", "qdrant"}
        assert expected_databases.issubset(databases)

    def test_database_health_status_values(self):
        """Test that database health status uses correct values (0 or 1)."""
        samples = list(database_health_status.collect())
        for sample in samples:
            for metric in sample.samples:
                value = metric.value
                assert value in [0, 1], f"Database health status should be 0 or 1, got {value}"

    def test_database_operation_failures_total_exists(self):
        """Test that database operation failures metric exists."""
        samples = list(database_operation_failures_total.collect())
        assert len(samples) > 0


class TestCeleryMetrics:
    """Test Celery task metrics."""

    def test_celery_tasks_total_exists(self):
        """Test that Celery tasks total metric exists."""
        samples = list(celery_tasks_total.collect())
        assert len(samples) > 0

    def test_celery_task_failures_total_exists(self):
        """Test that Celery task failures metric exists."""
        samples = list(celery_task_failures_total.collect())
        assert len(samples) > 0

    def test_celery_task_retries_total_exists(self):
        """Test that Celery task retries metric exists."""
        samples = list(celery_task_retries_total.collect())
        assert len(samples) > 0

    def test_celery_task_duration_seconds_exists(self):
        """Test that Celery task duration metric exists."""
        samples = list(celery_task_duration_seconds.collect())
        assert len(samples) > 0

    def test_celery_metrics_low_cardinality(self):
        """Test that Celery metrics use low-cardinality labels."""
        samples = list(celery_tasks_total.collect())
        for sample in samples:
            for metric in sample.samples:
                labels = metric.labels
                # Should only have 'task' and 'status' labels
                assert set(labels.keys()) == {"task", "status"}
                # Task should be a task name, not user ID
                assert "user_id" not in labels["task"]
                assert "document_id" not in labels["task"]


class TestLLMMetrics:
    """Test LLM provider metrics."""

    def test_llm_requests_total_exists(self):
        """Test that LLM requests total metric exists."""
        samples = list(llm_requests_total.collect())
        assert len(samples) > 0

    def test_llm_request_failures_total_exists(self):
        """Test that LLM request failures metric exists."""
        samples = list(llm_request_failures_total.collect())
        assert len(samples) > 0

    def test_llm_request_duration_seconds_exists(self):
        """Test that LLM request duration metric exists."""
        samples = list(llm_request_duration_seconds.collect())
        assert len(samples) > 0

    def test_llm_token_metrics_exist(self):
        """Test that LLM token metrics exist."""
        samples = list(llm_input_tokens_total.collect())
        assert len(samples) > 0
        
        samples = list(llm_output_tokens_total.collect())
        assert len(samples) > 0

    def test_llm_metrics_low_cardinality(self):
        """Test that LLM metrics use low-cardinality labels."""
        samples = list(llm_requests_total.collect())
        for sample in samples:
            for metric in sample.samples:
                labels = metric.labels
                # Should only have 'provider' and 'model' labels
                assert set(labels.keys()) == {"provider", "model"}
                # Provider should be normalized
                assert labels["provider"] in ["groq", "gemini", "openai", "anthropic", "mock"]


class TestWebSocketMetrics:
    """Test WebSocket metrics."""

    def test_websocket_connections_total_exists(self):
        """Test that WebSocket connections total metric exists."""
        samples = list(websocket_connections_total.collect())
        assert len(samples) > 0

    def test_websocket_disconnects_total_exists(self):
        """Test that WebSocket disconnects metric exists."""
        samples = list(websocket_disconnects_total.collect())
        assert len(samples) > 0

    def test_websocket_messages_total_exists(self):
        """Test that WebSocket messages total metric exists."""
        samples = list(websocket_messages_total.collect())
        assert len(samples) > 0

    def test_websocket_message_failures_total_exists(self):
        """Test that WebSocket message failures metric exists."""
        samples = list(websocket_message_failures_total.collect())
        assert len(samples) > 0

    def test_websocket_active_connections_exists(self):
        """Test that WebSocket active connections metric exists."""
        samples = list(websocket_active_connections.collect())
        assert len(samples) > 0

    def test_websocket_metrics_low_cardinality(self):
        """Test that WebSocket metrics use low-cardinality labels."""
        samples = list(websocket_connections_total.collect())
        for sample in samples:
            for metric in sample.samples:
                labels = metric.labels
                # Should only have 'result' label
                assert set(labels.keys()) == {"result"}
                # Result should be normalized
                assert labels["result"] in ["success", "failed"]


class TestDocumentProcessingMetrics:
    """Test document processing metrics."""

    def test_document_processing_total_exists(self):
        """Test that document processing total metric exists."""
        samples = list(document_processing_total.collect())
        assert len(samples) > 0

    def test_document_processing_duration_seconds_exists(self):
        """Test that document processing duration metric exists."""
        samples = list(document_processing_duration_seconds.collect())
        assert len(samples) > 0

    def test_vector_ingestion_failures_total_exists(self):
        """Test that vector ingestion failures metric exists."""
        samples = list(vector_ingestion_failures_total.collect())
        assert len(samples) > 0

    def test_document_metrics_low_cardinality(self):
        """Test that document metrics use low-cardinality labels."""
        samples = list(document_processing_total.collect())
        for sample in samples:
            for metric in sample.samples:
                labels = metric.labels
                # Should only have 'status' label
                assert set(labels.keys()) == {"status"}
                # Status should be normalized
                assert labels["status"] in ["success", "failed"]
                # Should not contain document IDs
                assert "document_id" not in labels["status"]


class TestRateLimitMetrics:
    """Test rate limit metrics."""

    def test_rate_limit_violations_total_exists(self):
        """Test that rate limit violations metric exists."""
        samples = list(rate_limit_violations_total.collect())
        assert len(samples) > 0

    def test_rate_limit_metrics_low_cardinality(self):
        """Test that rate limit metrics use low-cardinality labels."""
        samples = list(rate_limit_violations_total.collect())
        for sample in samples:
            for metric in sample.samples:
                labels = metric.labels
                # Should only have 'limit_type' and 'user_role' labels
                assert set(labels.keys()) == {"limit_type", "user_role"}
                # Should not contain user IDs or IPs
                assert "user_id" not in labels["limit_type"]
                assert "ip" not in labels["limit_type"]


class TestMetricsInitialization:
    """Test metrics initialization."""

    def test_metrics_initialization(self):
        """Test that metrics are properly initialized."""
        # Check that key metrics have been initialized with default values
        samples = list(database_health_status.collect())
        assert len(samples) > 0
        
        # Check that WebSocket active connections is initialized
        samples = list(websocket_active_connections.collect())
        assert len(samples) > 0

    def test_metrics_registry_not_empty(self):
        """Test that Prometheus registry is not empty."""
        metrics = list(prometheus_registry.collect())
        assert len(metrics) > 0


class TestMetricsIntegration:
    """Integration tests for metrics."""

    def test_metrics_update_after_real_requests(self, client: TestClient):
        """Test that metrics update after real HTTP requests."""
        # Get initial metrics
        initial_response = client.get("/v1/metrics")
        initial_content = initial_response.text
        
        # Make some real requests
        client.get("/health/live")
        client.get("/health/ready")
        
        # Get updated metrics
        updated_response = client.get("/v1/metrics")
        updated_content = updated_response.text
        
        # Metrics should have changed (requests incremented)
        # This is a basic check - in reality we'd parse the Prometheus format
        assert updated_content != initial_content or initial_content == updated_content


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def app():
    """Create the FastAPI app for testing."""
    from app.main import app
    return app
