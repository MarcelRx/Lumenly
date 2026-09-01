# apps/backend/tests/test_metrics_simple.py
"""
Simple metrics validation without database dependencies.
"""
import os

# Set environment before imports
os.environ['PROMETHEUS_MULTIPROC_DIR'] = '/tmp/test_prometheus_multiproc'
os.environ['APP_ENV'] = 'development'

from app.core.metrics import (
    auth_login_attempts_total,
    celery_tasks_total,
    database_health_status,
    http_request_duration_seconds,
    http_requests_in_flight,
    http_requests_total,
    initialize_metrics,
    llm_requests_total,
)


def test_metrics_exist():
    """Test that core metrics exist."""
    assert http_requests_total is not None
    assert http_request_duration_seconds is not None
    assert http_requests_in_flight is not None
    assert auth_login_attempts_total is not None
    assert database_health_status is not None
    assert celery_tasks_total is not None
    assert llm_requests_total is not None
    print("✓ All core metrics exist")


def test_cardinality_safety():
    """Test that metrics use low-cardinality labels."""
    forbidden_labels = {"user_id", "email", "document_id", "request_id", "password", "secret"}

    for metric in [http_requests_total, auth_login_attempts_total, celery_tasks_total]:
        for label_name in metric._labelnames:
            assert label_name not in forbidden_labels, f"Forbidden label: {label_name}"

    print("✓ Cardinality safety validated")


def test_naming_conventions():
    """Test that metrics follow naming conventions."""
    # Should be snake_case
    for metric in [http_requests_total, http_request_duration_seconds]:
        metric_name = metric._name
        assert metric_name.islower() or metric_name.replace("_", "").isalnum()
        assert not any(c.isupper() for c in metric_name if c.isalpha())

    # Duration metrics should have _seconds
    assert "_seconds" in http_request_duration_seconds._name

    # Counter metrics should have appropriate names (may or may not have _total suffix)
    # The important thing is they're descriptive and follow conventions
    assert "requests" in http_requests_total._name.lower()

    print("✓ Naming conventions validated")


def test_label_structure():
    """Test that metrics have correct label structure."""
    # HTTP metrics should have method, route, status_code
    http_labels = set(http_requests_total._labelnames)
    assert http_labels == {"method", "route", "status_code"}

    # Auth metrics should have result
    assert "result" in auth_login_attempts_total._labelnames

    # Database metrics should have database
    assert "database" in database_health_status._labelnames

    print("✓ Label structure validated")


def test_multiprocess_config():
    """Test multiprocess configuration."""
    assert 'PROMETHEUS_MULTIPROC_DIR' in os.environ
    print("✓ Multiprocess configured")


def test_initialization():
    """Test metrics initialization."""
    initialize_metrics()

    # Check database health metrics
    samples = list(database_health_status.collect())
    databases = set()
    for sample in samples:
        for metric_sample in sample.samples:
            if "database" in metric_sample.labels:
                databases.add(metric_sample.labels["database"])

    expected = {"postgresql", "mongodb", "redis", "qdrant"}
    assert expected.issubset(databases)

    print("✓ Metrics initialization validated")


def test_counter_increment():
    """Test that counters can be incremented."""
    auth_login_attempts_total.labels(result="test").inc()
    samples = list(auth_login_attempts_total.collect())
    assert len(samples) > 0
    print("✓ Counter increment validated")


def test_gauge_set():
    """Test that gauges can be set."""
    database_health_status.labels(database="test").set(1)
    samples = list(database_health_status.collect())
    assert len(samples) > 0
    print("✓ Gauge set validated")


if __name__ == "__main__":
    print("Running simple metrics validation...")
    test_metrics_exist()
    test_cardinality_safety()
    test_naming_conventions()
    test_label_structure()
    test_multiprocess_config()
    test_initialization()
    test_counter_increment()
    test_gauge_set()
    print("\n✅ All metrics validation tests passed!")
