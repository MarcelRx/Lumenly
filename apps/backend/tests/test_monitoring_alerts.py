"""
Monitoring and Alerting Test Suite

Tests for Phase 10.3 Production Monitoring & Alerting.

Coverage:
- Configuration validation
- Security tests
- Alert semantics tests
- Regression tests
"""

import re
from pathlib import Path

import pytest
import yaml


class TestPrometheusConfiguration:
    """Test Prometheus configuration validity."""

    def test_prometheus_config_exists(self):
        """Test that prometheus.yml exists."""
        prometheus_yml = Path(__file__).parent.parent.parent.parent / "prometheus.yml"
        assert prometheus_yml.exists(), "prometheus.yml must exist"

    def test_prometheus_config_valid_yaml(self):
        """Test that prometheus.yml is valid YAML."""
        prometheus_yml = Path(__file__).parent.parent.parent.parent / "prometheus.yml"
        with open(prometheus_yml) as f:
            config = yaml.safe_load(f)
        assert config is not None, "prometheus.yml must be valid YAML"
        assert "global" in config, "prometheus.yml must have global section"
        assert "scrape_configs" in config, "prometheus.yml must have scrape_configs"

    def test_prometheus_metrics_path_correct(self):
        """Test that Prometheus scrapes the correct metrics path."""
        prometheus_yml = Path(__file__).parent.parent.parent.parent / "prometheus.yml"
        with open(prometheus_yml) as f:
            config = yaml.safe_load(f)

        scrape_configs = config.get("scrape_configs", [])
        assert len(scrape_configs) > 0, "prometheus.yml must have scrape configs"

        for scrape_config in scrape_configs:
            metrics_path = scrape_config.get("metrics_path", "/metrics")
            assert metrics_path == "/v1/metrics", f"Metrics path must be /v1/metrics, got {metrics_path}"

    def test_prometheus_rule_files_configured(self):
        """Test that Prometheus rule files are configured."""
        prometheus_yml = Path(__file__).parent.parent.parent.parent / "prometheus.yml"
        with open(prometheus_yml) as f:
            config = yaml.safe_load(f)

        rule_files = config.get("rule_files", [])
        assert len(rule_files) > 0, "prometheus.yml must have rule_files configured"
        assert any("rules" in rf for rf in rule_files), "rule_files must include rules directory"

    def test_prometheus_alertmanager_configured(self):
        """Test that Prometheus is configured to use Alertmanager."""
        prometheus_yml = Path(__file__).parent.parent.parent.parent / "prometheus.yml"
        with open(prometheus_yml) as f:
            config = yaml.safe_load(f)

        alerting = config.get("alerting", {})
        assert alerting is not None, "prometheus.yml must have alerting section"
        assert "alertmanagers" in alerting, "prometheus.yml must have alertmanagers configured"


class TestAlertRules:
    """Test alert rule files."""

    def test_alert_rules_directory_exists(self):
        """Test that alert rules directory exists."""
        rules_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "prometheus" / "rules"
        assert rules_dir.exists(), "Alert rules directory must exist"

    def test_alert_rule_files_exist(self):
        """Test that all required alert rule files exist."""
        rules_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "prometheus" / "rules"
        required_files = ["backend.yml", "dependencies.yml", "celery.yml", "security.yml", "llm.yml"]

        for required_file in required_files:
            rule_file = rules_dir / required_file
            assert rule_file.exists(), f"Alert rule file {required_file} must exist"

    def test_alert_rules_valid_yaml(self):
        """Test that all alert rule files are valid YAML."""
        rules_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "prometheus" / "rules"

        for rule_file in rules_dir.glob("*.yml"):
            with open(rule_file) as f:
                config = yaml.safe_load(f)
            assert config is not None, f"{rule_file.name} must be valid YAML"
            assert "groups" in config, f"{rule_file.name} must have groups"

    def test_alert_rules_have_required_fields(self):
        """Test that all alerts have required fields."""
        rules_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "prometheus" / "rules"

        for rule_file in rules_dir.glob("*.yml"):
            with open(rule_file) as f:
                config = yaml.safe_load(f)

            for group in config.get("groups", []):
                for rule in group.get("rules", []):
                    assert "alert" in rule, f"Alert in {rule_file.name} must have 'alert' field"
                    assert "expr" in rule, f"Alert {rule.get('alert')} in {rule_file.name} must have 'expr' field"
                    assert "for" in rule, f"Alert {rule.get('alert')} in {rule_file.name} must have 'for' field"
                    assert "labels" in rule, f"Alert {rule.get('alert')} in {rule_file.name} must have 'labels' field"
                    assert "annotations" in rule, f"Alert {rule.get('alert')} in {rule_file.name} must have 'annotations' field"

    def test_alert_rules_have_severity(self):
        """Test that all alerts have severity label."""
        rules_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "prometheus" / "rules"

        for rule_file in rules_dir.glob("*.yml"):
            with open(rule_file) as f:
                config = yaml.safe_load(f)

            for group in config.get("groups", []):
                for rule in group.get("rules", []):
                    labels = rule.get("labels", {})
                    assert "severity" in labels, f"Alert {rule.get('alert')} in {rule_file.name} must have severity label"
                    assert labels["severity"] in ["P0", "P1", "P2", "P3"], \
                        f"Alert {rule.get('alert')} in {rule_file.name} must have valid severity (P0-P3)"

    def test_alert_rules_have_runbook(self):
        """Test that all alerts have runbook reference."""
        rules_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "prometheus" / "rules"

        for rule_file in rules_dir.glob("*.yml"):
            with open(rule_file) as f:
                config = yaml.safe_load(f)

            for group in config.get("groups", []):
                for rule in group.get("rules", []):
                    annotations = rule.get("annotations", {})
                    assert "runbook" in annotations, f"Alert {rule.get('alert')} in {rule_file.name} must have runbook annotation"

    def test_no_duplicate_alert_names(self):
        """Test that alert names are unique across all rule files."""
        rules_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "prometheus" / "rules"
        alert_names = []

        for rule_file in rules_dir.glob("*.yml"):
            with open(rule_file) as f:
                config = yaml.safe_load(f)

            for group in config.get("groups", []):
                for rule in group.get("rules", []):
                    alert_name = rule.get("alert")
                    assert alert_name not in alert_names, f"Duplicate alert name: {alert_name}"
                    alert_names.append(alert_name)


class TestAlertmanagerConfiguration:
    """Test Alertmanager configuration."""

    def test_alertmanager_config_exists(self):
        """Test that alertmanager.yml exists."""
        alertmanager_yml = Path(__file__).parent.parent.parent.parent / "monitoring" / "alertmanager" / "alertmanager.yml"
        assert alertmanager_yml.exists(), "alertmanager.yml must exist"

    def test_alertmanager_config_valid_yaml(self):
        """Test that alertmanager.yml is valid YAML."""
        alertmanager_yml = Path(__file__).parent.parent.parent.parent / "monitoring" / "alertmanager" / "alertmanager.yml"
        with open(alertmanager_yml) as f:
            config = yaml.safe_load(f)
        assert config is not None, "alertmanager.yml must be valid YAML"

    def test_alertmanager_has_receivers(self):
        """Test that Alertmanager has receivers configured."""
        alertmanager_yml = Path(__file__).parent.parent.parent.parent / "monitoring" / "alertmanager" / "alertmanager.yml"
        with open(alertmanager_yml) as f:
            config = yaml.safe_load(f)

        receivers = config.get("receivers", [])
        assert len(receivers) > 0, "alertmanager.yml must have receivers"

    def test_alertmanager_has_route(self):
        """Test that Alertmanager has route configured."""
        alertmanager_yml = Path(__file__).parent.parent.parent.parent / "monitoring" / "alertmanager" / "alertmanager.yml"
        with open(alertmanager_yml) as f:
            config = yaml.safe_load(f)

        route = config.get("route")
        assert route is not None, "alertmanager.yml must have route"


class TestSecurity:
    """Test security aspects of monitoring configuration."""

    SENSITIVE_PATTERNS = [
        r'password["\s]*[:=]["\s]*[^\s"]+',
        r'api[_-]?key["\s]*[:=]["\s]*[^\s"]+',
        r'jwt["\s]*[:=]["\s]*[^\s"]+',
        r'token["\s]*[:=]["\s]*[^\s"]+',
        r'secret["\s]*[:=]["\s]*[^\s"]+',
        r'Bearer\s+[A-Za-z0-9\._-]+',
        r'sk-[a-zA-Z0-9]{20,}',
        r'AIza[a-zA-Z0-9_-]{35}',
    ]

    def test_no_secrets_in_prometheus_config(self):
        """Test that prometheus.yml contains no secrets."""
        prometheus_yml = Path(__file__).parent.parent.parent.parent / "prometheus.yml"
        with open(prometheus_yml) as f:
            content = f.read()

        for pattern in self.SENSITIVE_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            assert len(matches) == 0, f"prometheus.yml contains potential secret: {matches[0]}"

    def test_no_secrets_in_alert_rules(self):
        """Test that alert rules contain no secrets."""
        rules_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "prometheus" / "rules"

        for rule_file in rules_dir.glob("*.yml"):
            with open(rule_file) as f:
                content = f.read()

            for pattern in self.SENSITIVE_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                assert len(matches) == 0, f"{rule_file.name} contains potential secret: {matches[0]}"

    def test_no_secrets_in_alertmanager_config(self):
        """Test that alertmanager.yml contains no secrets."""
        alertmanager_yml = Path(__file__).parent.parent.parent.parent / "monitoring" / "alertmanager" / "alertmanager.yml"
        with open(alertmanager_yml) as f:
            content = f.read()

        for pattern in self.SENSITIVE_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            assert len(matches) == 0, f"alertmanager.yml contains potential secret: {matches[0]}"

    def test_no_user_ids_in_alert_labels(self):
        """Test that alert labels do not contain user IDs."""
        rules_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "prometheus" / "rules"

        for rule_file in rules_dir.glob("*.yml"):
            with open(rule_file) as f:
                config = yaml.safe_load(f)

            for group in config.get("groups", []):
                for rule in group.get("rules", []):
                    labels = rule.get("labels", {})
                    for key, value in labels.items():
                        assert "user_id" not in key.lower(), f"Alert {rule.get('alert')} has user_id label"
                        assert "email" not in key.lower(), f"Alert {rule.get('alert')} has email label"
                        assert "document_id" not in key.lower(), f"Alert {rule.get('alert')} has document_id label"

    def test_no_dynamic_paths_in_alert_labels(self):
        """Test that alert labels do not contain dynamic paths."""
        rules_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "prometheus" / "rules"

        for rule_file in rules_dir.glob("*.yml"):
            with open(rule_file) as f:
                config = yaml.safe_load(f)

            for group in config.get("groups", []):
                for rule in group.get("rules", []):
                    labels = rule.get("labels", {})
                    for key, value in labels.items():
                        assert "path" not in key.lower(), f"Alert {rule.get('alert')} has path label"

    def test_no_secrets_in_grafana_dashboards(self):
        """Test that Grafana dashboards contain no secrets."""
        dashboards_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "grafana" / "dashboards"

        for dashboard_file in dashboards_dir.glob("*.json"):
            with open(dashboard_file) as f:
                content = f.read()

            for pattern in self.SENSITIVE_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                assert len(matches) == 0, f"{dashboard_file.name} contains potential secret: {matches[0]}"


class TestRunbooks:
    """Test operational runbooks."""

    def test_runbooks_directory_exists(self):
        """Test that runbooks directory exists."""
        runbooks_dir = Path(__file__).parent.parent.parent.parent / "docs" / "runbooks"
        assert runbooks_dir.exists(), "Runbooks directory must exist"

    def test_required_runbooks_exist(self):
        """Test that all required runbooks exist."""
        runbooks_dir = Path(__file__).parent.parent.parent.parent / "docs" / "runbooks"
        required_runbooks = [
            "backend-down.md",
            "high-error-rate.md",
            "high-latency.md",
            "postgres-unavailable.md",
            "mongodb-unavailable.md",
            "redis-unavailable.md",
            "qdrant-unavailable.md",
            "celery-failures.md",
            "llm-provider-failure.md",
            "security-anomaly.md",
        ]

        for required_runbook in required_runbooks:
            runbook_file = runbooks_dir / required_runbook
            assert runbook_file.exists(), f"Runbook {required_runbook} must exist"

    def test_runbooks_have_required_sections(self):
        """Test that runbooks have required sections."""
        runbooks_dir = Path(__file__).parent.parent.parent.parent / "docs" / "runbooks"
        required_sections = [
            "Alert Meaning",
            "Severity",
            "Immediate Checks",
            "Recovery Procedure",
        ]

        for runbook_file in runbooks_dir.glob("*.md"):
            with open(runbook_file) as f:
                content = f.read()

            for section in required_sections:
                assert section in content, f"{runbook_file.name} must have section: {section}"


class TestGrafanaConfiguration:
    """Test Grafana configuration."""

    def test_grafana_provisioning_exists(self):
        """Test that Grafana provisioning directory exists."""
        provisioning_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "grafana" / "provisioning"
        assert provisioning_dir.exists(), "Grafana provisioning directory must exist"

    def test_grafana_datasource_config_exists(self):
        """Test that Grafana datasource configuration exists."""
        datasource_file = Path(__file__).parent.parent.parent.parent / "monitoring" / "grafana" / "provisioning" / "datasources" / "prometheus.yml"
        assert datasource_file.exists(), "Grafana datasource configuration must exist"

    def test_grafana_dashboard_config_exists(self):
        """Test that Grafana dashboard provisioning configuration exists."""
        dashboard_file = Path(__file__).parent.parent.parent.parent / "monitoring" / "grafana" / "provisioning" / "dashboards" / "dashboards.yml"
        assert dashboard_file.exists(), "Grafana dashboard provisioning configuration must exist"

    def test_grafana_dashboards_exist(self):
        """Test that all required Grafana dashboards exist."""
        dashboards_dir = Path(__file__).parent.parent.parent.parent / "monitoring" / "grafana" / "dashboards"
        required_dashboards = [
            "api-overview.json",
            "dependencies.json",
            "celery.json",
            "ai-llm.json",
            "security.json",
        ]

        for required_dashboard in required_dashboards:
            dashboard_file = dashboards_dir / required_dashboard
            assert dashboard_file.exists(), f"{required_dashboard} must exist"


class TestDockerComposeConfiguration:
    """Test Docker Compose configuration for monitoring stack."""

    def test_docker_compose_exists(self):
        """Test that docker-compose.yml exists."""
        docker_compose = Path(__file__).parent.parent.parent.parent / ".docker" / "docker-compose.yml"
        assert docker_compose.exists(), "docker-compose.yml must exist"

    def test_prometheus_service_exists(self):
        """Test that Prometheus service exists in docker-compose.yml."""
        docker_compose = Path(__file__).parent.parent.parent.parent / ".docker" / "docker-compose.yml"
        with open(docker_compose) as f:
            config = yaml.safe_load(f)

        services = config.get("services", {})
        assert "prometheus" in services, "Prometheus service must exist in docker-compose.yml"

    def test_alertmanager_service_exists(self):
        """Test that Alertmanager service exists in docker-compose.yml."""
        docker_compose = Path(__file__).parent.parent.parent.parent / ".docker" / "docker-compose.yml"
        with open(docker_compose) as f:
            config = yaml.safe_load(f)

        services = config.get("services", {})
        assert "alertmanager" in services, "Alertmanager service must exist in docker-compose.yml"

    def test_grafana_service_exists(self):
        """Test that Grafana service exists in docker-compose.yml."""
        docker_compose = Path(__file__).parent.parent.parent.parent / ".docker" / "docker-compose.yml"
        with open(docker_compose) as f:
            config = yaml.safe_load(f)

        services = config.get("services", {})
        assert "grafana" in services, "Grafana service must exist in docker-compose.yml"

    def test_prometheus_rule_files_mounted(self):
        """Test that Prometheus rule files are mounted in docker-compose.yml."""
        docker_compose = Path(__file__).parent.parent.parent.parent / ".docker" / "docker-compose.yml"
        with open(docker_compose) as f:
            config = yaml.safe_load(f)

        prometheus_service = config.get("services", {}).get("prometheus", {})
        volumes = prometheus_service.get("volumes", [])

        rule_mounted = any("rules" in vol for vol in volumes)
        assert rule_mounted, "Prometheus rule files must be mounted in docker-compose.yml"

    def test_prometheus_pinned_version(self):
        """Test that Prometheus uses a pinned version, not :latest."""
        docker_compose = Path(__file__).parent.parent.parent.parent / ".docker" / "docker-compose.yml"
        with open(docker_compose) as f:
            config = yaml.safe_load(f)

        prometheus_service = config.get("services", {}).get("prometheus", {})
        image = prometheus_service.get("image", "")
        assert ":latest" not in image, "Prometheus must use a pinned version, not :latest"

    def test_alertmanager_pinned_version(self):
        """Test that Alertmanager uses a pinned version, not :latest."""
        docker_compose = Path(__file__).parent.parent.parent.parent / ".docker" / "docker-compose.yml"
        with open(docker_compose) as f:
            config = yaml.safe_load(f)

        alertmanager_service = config.get("services", {}).get("alertmanager", {})
        image = alertmanager_service.get("image", "")
        assert ":latest" not in image, "Alertmanager must use a pinned version, not :latest"

    def test_grafana_pinned_version(self):
        """Test that Grafana uses a pinned version, not :latest."""
        docker_compose = Path(__file__).parent.parent.parent.parent / ".docker" / "docker-compose.yml"
        with open(docker_compose) as f:
            config = yaml.safe_load(f)

        grafana_service = config.get("services", {}).get("grafana", {})
        image = grafana_service.get("image", "")
        assert ":latest" not in image, "Grafana must use a pinned version, not :latest"


class TestRegression:
    """Regression tests to ensure existing functionality remains intact."""

    def test_metrics_endpoint_path(self):
        """Test that metrics endpoint is at /v1/metrics."""
        from app.api.endpoints.metrics import router
        routes = [route.path for route in router.routes]
        assert "/metrics" in routes, "Metrics endpoint must be at /metrics"

    def test_health_endpoints_exist(self):
        """Test that health endpoints exist."""
        # This would require importing the FastAPI app
        # For now, we'll just check that the files exist
        main_py = Path(__file__).parent.parent / "app" / "main.py"
        assert main_py.exists(), "main.py must exist"

        with open(main_py) as f:
            content = f.read()

        assert "/health/live" in content, "main.py must have /health/live endpoint"
        assert "/health/ready" in content, "main.py must have /health/ready endpoint"

    def test_metrics_multiprocess_support(self):
        """Test that multiprocess mode is configured."""
        metrics_py = Path(__file__).parent.parent / "app" / "core" / "metrics.py"
        with open(metrics_py) as f:
            content = f.read()

        assert "PROMETHEUS_MULTIPROC_DIR" in content, "metrics.py must configure PROMETHEUS_MULTIPROC_DIR"
        assert "MultiProcessCollector" in content, "metrics.py must use MultiProcessCollector"

    def test_celery_synchronous_architecture(self):
        """Test that Celery architecture remains synchronous."""
        celery_py = Path(__file__).parent.parent / "app" / "core" / "celery_app.py"
        with open(celery_py) as f:
            content = f.read()

        # Check that there are no async/await imports in celery config
        assert "asyncio" not in content.lower(), "celery_app.py should not import asyncio"
        assert "await" not in content, "celery_app.py should not use await"

    def test_cardinality_protection(self):
        """Test that cardinality protection is in place."""
        metrics_middleware = Path(__file__).parent.parent / "app" / "middleware" / "metrics.py"
        with open(metrics_middleware) as f:
            content = f.read()

        assert "get_route_template" in content, "metrics middleware must use route templates"
        assert "{id}" in content or "{uuid}" in content, "metrics middleware must normalize dynamic segments"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
