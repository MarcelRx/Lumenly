# apps/backend/tests/test_metrics_cardinality.py
"""
Cardinality tests for metrics to ensure low-cardinality labels.

Tests that metrics do not use high-cardinality identifiers like user_id,
document_id, etc., which can damage Prometheus performance and expose
sensitive data.
"""
import pytest
from prometheus_client import REGISTRY as prometheus_registry

from app.core.metrics import (
    # Import all metrics to check their labels
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_flight,
    auth_login_attempts_total,
    auth_token_refresh_total,
    auth_registration_attempts_total,
    security_authorization_failures_total,
    security_cross_tenant_attempts_total,
    security_rate_limit_exceeded_total,
    database_health_status,
    database_operation_failures_total,
    celery_tasks_total,
    celery_task_failures_total,
    celery_task_retries_total,
    celery_task_duration_seconds,
    llm_requests_total,
    llm_request_failures_total,
    llm_request_duration_seconds,
    llm_input_tokens_total,
    llm_output_tokens_total,
    websocket_connections_total,
    websocket_disconnects_total,
    websocket_messages_total,
    websocket_message_failures_total,
    websocket_active_connections,
    document_processing_total,
    document_processing_duration_seconds,
    vector_ingestion_failures_total,
    rate_limit_violations_total,
)


class TestMetricsCardinality:
    """Test that metrics use low-cardinality labels."""

    # Forbidden label names that would cause high cardinality
    FORBIDDEN_LABELS = {
        "user_id",
        "email",
        "username",
        "document_id",
        "journal_id",
        "goal_id",
        "habit_id",
        "session_id",
        "request_id",
        "resource_id",
        "jwt",
        "token",
        "ip",
        "raw_url",
        "query",
        "password",
        "secret",
        "api_key",
        "authorization",
        "tenant_id",
        "organization_id",
        "workspace_id",
        "conversation_id",
        "message_id",
        "vector_id",
        "chunk_id",
        "embedding_id",
        "tool_call_id",
        "coaching_session_id",
    }

    def test_http_metrics_cardinality(self):
        """Test that HTTP metrics use low-cardinality labels."""
        metrics = [
            http_requests_total,
            http_request_duration_seconds,
            http_requests_in_flight,
        ]
        
        for metric in metrics:
            samples = list(metric.collect())
            for sample in samples:
                for metric_sample in sample.samples:
                    labels = metric_sample.labels
                    self._check_labels_forbidden(labels, metric.name)

    def test_auth_metrics_cardinality(self):
        """Test that authentication metrics use low-cardinality labels."""
        metrics = [
            auth_login_attempts_total,
            auth_token_refresh_total,
            auth_registration_attempts_total,
        ]
        
        for metric in metrics:
            samples = list(metric.collect())
            for sample in samples:
                for metric_sample in sample.samples:
                    labels = metric_sample.labels
                    self._check_labels_forbidden(labels, metric.name)

    def test_security_metrics_cardinality(self):
        """Test that security metrics use low-cardinality labels."""
        metrics = [
            security_authorization_failures_total,
            security_cross_tenant_attempts_total,
            security_rate_limit_exceeded_total,
        ]
        
        for metric in metrics:
            samples = list(metric.collect())
            for sample in samples:
                for metric_sample in sample.samples:
                    labels = metric_sample.labels
                    self._check_labels_forbidden(labels, metric.name)

    def test_database_metrics_cardinality(self):
        """Test that database metrics use low-cardinality labels."""
        metrics = [
            database_health_status,
            database_operation_failures_total,
        ]
        
        for metric in metrics:
            samples = list(metric.collect())
            for sample in samples:
                for metric_sample in sample.samples:
                    labels = metric_sample.labels
                    self._check_labels_forbidden(labels, metric.name)

    def test_celery_metrics_cardinality(self):
        """Test that Celery metrics use low-cardinality labels."""
        metrics = [
            celery_tasks_total,
            celery_task_failures_total,
            celery_task_retries_total,
            celery_task_duration_seconds,
        ]
        
        for metric in metrics:
            samples = list(metric.collect())
            for sample in samples:
                for metric_sample in sample.samples:
                    labels = metric_sample.labels
                    self._check_labels_forbidden(labels, metric.name)
                    # Specifically check that task names don't contain IDs
                    if "task" in labels:
                        task_name = labels["task"]
                        self._check_task_name_for_ids(task_name, metric.name)

    def test_llm_metrics_cardinality(self):
        """Test that LLM metrics use low-cardinality labels."""
        metrics = [
            llm_requests_total,
            llm_request_failures_total,
            llm_request_duration_seconds,
            llm_input_tokens_total,
            llm_output_tokens_total,
        ]
        
        for metric in metrics:
            samples = list(metric.collect())
            for sample in samples:
                for metric_sample in sample.samples:
                    labels = metric_sample.labels
                    self._check_labels_forbidden(labels, metric.name)

    def test_websocket_metrics_cardinality(self):
        """Test that WebSocket metrics use low-cardinality labels."""
        metrics = [
            websocket_connections_total,
            websocket_disconnects_total,
            websocket_messages_total,
            websocket_message_failures_total,
            websocket_active_connections,
        ]
        
        for metric in metrics:
            samples = list(metric.collect())
            for sample in samples:
                for metric_sample in sample.samples:
                    labels = metric_sample.labels
                    self._check_labels_forbidden(labels, metric.name)

    def test_document_metrics_cardinality(self):
        """Test that document processing metrics use low-cardinality labels."""
        metrics = [
            document_processing_total,
            document_processing_duration_seconds,
            vector_ingestion_failures_total,
        ]
        
        for metric in metrics:
            samples = list(metric.collect())
            for sample in samples:
                for metric_sample in sample.samples:
                    labels = metric_sample.labels
                    self._check_labels_forbidden(labels, metric.name)

    def test_rate_limit_metrics_cardinality(self):
        """Test that rate limit metrics use low-cardinality labels."""
        metrics = [
            rate_limit_violations_total,
        ]
        
        for metric in metrics:
            samples = list(metric.collect())
            for sample in samples:
                for metric_sample in sample.samples:
                    labels = metric_sample.labels
                    self._check_labels_forbidden(labels, metric.name)

    def test_all_metrics_cardinality(self):
        """Test all metrics in the registry for forbidden labels."""
        all_metrics = list(prometheus_registry.collect())
        
        for metric_family in all_metrics:
            for sample in metric_family.samples:
                labels = sample.labels
                self._check_labels_forbidden(labels, metric_family.name)

    def _check_labels_forbidden(self, labels, metric_name):
        """Check that labels do not contain forbidden high-cardinality identifiers."""
        for label_name, label_value in labels.items():
            # Check label name
            assert label_name not in self.FORBIDDEN_LABELS, (
                f"Metric '{metric_name}' uses forbidden label name: {label_name}"
            )
            
            # Check label value for forbidden patterns
            label_value_lower = label_value.lower()
            for forbidden in self.FORBIDDEN_LABELS:
                # Check if forbidden term appears as a value
                if forbidden in label_value_lower:
                    # Allow some legitimate uses
                    if forbidden == "token" and "token" in ["refresh_token", "access_token"]:
                        continue  # Allow in normalized result labels
                    if forbidden == "request" and "request" in ["http_request"]:
                        continue  # Allow in metric names
                    assert False, (
                        f"Metric '{metric_name}' label '{label_name}' has forbidden value "
                        f"containing '{forbidden}': {label_value}"
                    )

    def _check_task_name_for_ids(self, task_name, metric_name):
        """Check that task names don't contain IDs."""
        # Task names should be descriptive, not contain IDs
        forbidden_patterns = ["_id", "uuid", "-id", ".id"]
        for pattern in forbidden_patterns:
            assert pattern not in task_name.lower(), (
                f"Metric '{metric_name}' task name '{task_name}' contains "
                f"forbidden pattern '{pattern}' (possible ID)"
            )


class TestMetricsLabelNormalization:
    """Test that metric labels use normalized values."""

    def test_http_status_code_normalization(self):
        """Test that HTTP status codes are normalized."""
        samples = list(http_requests_total.collect())
        for sample in samples:
            for metric_sample in sample.samples:
                if "status_code" in metric_sample.labels:
                    status_code = metric_sample.labels["status_code"]
                    # Should be a string like "200", "404", etc.
                    assert status_code.isdigit(), f"Status code should be numeric: {status_code}"
                    assert int(status_code) in range(100, 600), f"Invalid status code: {status_code}"

    def test_auth_result_normalization(self):
        """Test that auth result labels are normalized."""
        samples = list(auth_login_attempts_total.collect())
        normalized_results = {"success", "invalid_credentials", "inactive_user", "error"}
        
        for sample in samples:
            for metric_sample in sample.samples:
                if "result" in metric_sample.labels:
                    result = metric_sample.labels["result"]
                    assert result in normalized_results, f"Non-normalized auth result: {result}"

    def test_security_resource_type_normalization(self):
        """Test that security resource type labels are normalized."""
        samples = list(security_authorization_failures_total.collect())
        # Expected resource types
        expected_types = {"tool_execution", "unregistered_tool", "habit", "goal", "journal"}
        
        for sample in samples:
            for metric_sample in sample.samples:
                if "resource_type" in metric_sample.labels:
                    resource_type = metric_sample.labels["resource_type"]
                    # Should be lowercase, no spaces
                    assert resource_type.islower() or resource_type.replace("_", "").isalnum()
                    assert " " not in resource_type

    def test_llm_provider_normalization(self):
        """Test that LLM provider labels are normalized."""
        samples = list(llm_requests_total.collect())
        normalized_providers = {"groq", "gemini", "openai", "anthropic", "mock"}
        
        for sample in samples:
            for metric_sample in sample.samples:
                if "provider" in metric_sample.labels:
                    provider = metric_sample.labels["provider"]
                    assert provider.lower() in normalized_providers, f"Non-normalized provider: {provider}"

    def test_websocket_result_normalization(self):
        """Test that WebSocket result labels are normalized."""
        samples = list(websocket_connections_total.collect())
        normalized_results = {"success", "failed"}
        
        for sample in samples:
            for metric_sample in sample.samples:
                if "result" in metric_sample.labels:
                    result = metric_sample.labels["result"]
                    assert result in normalized_results, f"Non-normalized WebSocket result: {result}"

    def test_document_status_normalization(self):
        """Test that document status labels are normalized."""
        samples = list(document_processing_total.collect())
        normalized_statuses = {"success", "failed"}
        
        for sample in samples:
            for metric_sample in sample.samples:
                if "status" in metric_sample.labels:
                    status = metric_sample.labels["status"]
                    assert status in normalized_statuses, f"Non-normalized document status: {status}"

    def test_database_name_normalization(self):
        """Test that database name labels are normalized."""
        samples = list(database_health_status.collect())
        normalized_databases = {"postgresql", "mongodb", "redis", "qdrant"}
        
        for sample in samples:
            for metric_sample in sample.samples:
                if "database" in metric_sample.labels:
                    database = metric_sample.labels["database"]
                    assert database in normalized_databases, f"Non-normalized database name: {database}"


class TestMetricsLabelCount:
    """Test that metrics don't have too many label combinations."""

    def test_http_metrics_label_count(self):
        """Test that HTTP metrics have reasonable label counts."""
        samples = list(http_requests_total.collect())
        # Count unique label combinations
        label_combinations = set()
        for sample in samples:
            for metric_sample in sample.samples:
                # Create a tuple of sorted label items for uniqueness
                labels_tuple = tuple(sorted(metric_sample.labels.items()))
                label_combinations.add(labels_tuple)
        
        # Should not have excessive combinations (this is a basic check)
        # In a real system, this would be based on actual traffic patterns
        assert len(label_combinations) < 1000, "Too many HTTP metric label combinations"

    def test_celery_metrics_label_count(self):
        """Test that Celery metrics have reasonable label counts."""
        samples = list(celery_tasks_total.collect())
        label_combinations = set()
        for sample in samples:
            for metric_sample in sample.samples:
                labels_tuple = tuple(sorted(metric_sample.labels.items()))
                label_combinations.add(labels_tuple)
        
        # Should be limited by number of task types
        assert len(label_combinations) < 100, "Too many Celery metric label combinations"

    def test_llm_metrics_label_count(self):
        """Test that LLM metrics have reasonable label counts."""
        samples = list(llm_requests_total.collect())
        label_combinations = set()
        for sample in samples:
            for metric_sample in sample.samples:
                labels_tuple = tuple(sorted(metric_sample.labels.items()))
                label_combinations.add(labels_tuple)
        
        # Should be limited by number of providers and models
        assert len(label_combinations) < 50, "Too many LLM metric label combinations"


class TestMetricsLabelValues:
    """Test that metric label values are safe and predictable."""

    def test_no_uuids_in_labels(self):
        """Test that no label values contain UUIDs."""
        all_metrics = list(prometheus_registry.collect())
        
        for metric_family in all_metrics:
            for sample in metric_family.samples:
                for label_name, label_value in sample.labels.items():
                    # Check for UUID pattern
                    import re
                    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
                    if re.search(uuid_pattern, label_value.lower()):
                        assert False, (
                            f"Metric '{metric_family.name}' label '{label_name}' contains "
                            f"UUID: {label_value}"
                        )

    def test_no_timestamps_in_labels(self):
        """Test that no label values contain timestamps."""
        all_metrics = list(prometheus_registry.collect())
        
        for metric_family in all_metrics:
            for sample in metric_family.samples:
                for label_name, label_value in sample.labels.items():
                    # Check for timestamp patterns (ISO 8601, Unix timestamps)
                    import re
                    iso_pattern = r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}'
                    unix_pattern = r'^\d{10,13}$'  # Unix timestamp
                    
                    if re.search(iso_pattern, label_value):
                        assert False, (
                            f"Metric '{metric_family.name}' label '{label_name}' contains "
                            f"timestamp: {label_value}"
                        )
                    if re.match(unix_pattern, label_value):
                        assert False, (
                            f"Metric '{metric_family.name}' label '{label_name}' contains "
                            f"Unix timestamp: {label_value}"
                        )

    def test_no_urls_in_labels(self):
        """Test that no label values contain full URLs."""
        all_metrics = list(prometheus_registry.collect())
        
        for metric_family in all_metrics:
            for sample in metric_family.samples:
                for label_name, label_value in sample.labels.items():
                    # Check for URL patterns
                    import re
                    url_pattern = r'https?://[^\s]+'
                    
                    if re.search(url_pattern, label_value):
                        # Allow route patterns but not full URLs with domains
                        if 'http://' in label_value or 'https://' in label_value:
                            if '.' in label_value.split('/')[2]:  # Has domain
                                assert False, (
                                    f"Metric '{metric_family.name}' label '{label_name}' contains "
                                    f"full URL: {label_value}"
                                )

    def test_label_values_length(self):
        """Test that label values have reasonable length."""
        all_metrics = list(prometheus_registry.collect())
        
        for metric_family in all_metrics:
            for sample in metric_family.samples:
                for label_name, label_value in sample.labels.items():
                    # Label values should not be excessively long
                    assert len(label_value) < 200, (
                        f"Metric '{metric_family.name}' label '{label_name}' value is too long: "
                        f"{len(label_value)} characters"
                    )

    def test_label_values_special_chars(self):
        """Test that label values don't have problematic special characters."""
        all_metrics = list(prometheus_registry.collect())
        
        for metric_family in all_metrics:
            for sample in metric_family.samples:
                for label_name, label_value in sample.labels.items():
                    # Prometheus allows limited special characters
                    # Check for problematic characters
                    problematic_chars = ['\n', '\r', '\t', '\\', '"', "'"]
                    for char in problematic_chars:
                        assert char not in label_value, (
                            f"Metric '{metric_family.name}' label '{label_name}' contains "
                            f"problematic character '{char}': {label_value}"
                        )
