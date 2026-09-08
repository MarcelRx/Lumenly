# apps/backend/tests/test_metrics_security.py
"""
Security tests for metrics to ensure no sensitive data is exposed.

Tests for secret leakage, user data exposure, and other security concerns
in the metrics implementation.
"""
import pytest
from fastapi.testclient import TestClient


class TestMetricsSecretLeakage:
    """Test that metrics do not expose secrets."""

    def test_metrics_no_password_exposure(self, client: TestClient):
        """Test that metrics do not expose passwords."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for password patterns
        assert "password" not in content
        assert "passwd" not in content
        assert "pwd" not in content or "pwd" in "/v1/metrics"  # Allow in URLs

    def test_metrics_no_api_key_exposure(self, client: TestClient):
        """Test that metrics do not expose API keys."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for API key patterns
        assert "api_key" not in content
        assert "apikey" not in content
        assert "api-key" not in content

    def test_metrics_no_jwt_exposure(self, client: TestClient):
        """Test that metrics do not expose JWT tokens."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for JWT patterns
        assert "jwt" not in content
        assert "json web token" not in content
        # Check for JWT-like strings (eyJ...)
        assert "eyJ" not in content

    def test_metrics_no_token_exposure(self, client: TestClient):
        """Test that metrics do not expose tokens."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for token patterns
        # Allow "token" in metric names like "auth_token_refresh_total"
        lines = content.split('\n')
        for line in lines:
            if 'token' in line and 'auth_token' not in line and 'refresh_token' not in line:
                # If token appears outside of expected metric names, fail
                # This is a conservative check
                if not line.startswith('#') and 'token' in line:
                    # Check if it's a comment or metric definition
                    if not line.strip().startswith('#'):
                        # Token should only be in metric names, not values
                        parts = line.split()
                        if len(parts) > 1:
                            # This should be a metric value, not a token
                            assert False, f"Unexpected token in metrics: {line}"

    def test_metrics_no_secret_exposure(self, client: TestClient):
        """Test that metrics do not expose secrets."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for secret patterns
        assert "secret" not in content or "secret" in "# TYPE" or "secret" in "# HELP"

    def test_metrics_no_authorization_header_exposure(self, client: TestClient):
        """Test that metrics do not expose authorization headers."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for actual authorization header values, not metric names
        lines = content.split('\n')
        for line in lines:
            if '=' in line and not line.startswith('#'):
                # This is a metric line with a value
                value_part = line.split('=')[1].strip()
                # Check if value looks like an authorization header
                if 'bearer' in value_part or 'basic' in value_part:
                    raise AssertionError(f"Authorization header pattern found in metric value: {line}")
                # Check for JWT-like patterns in values
                if 'eyJ' in value_part:
                    raise AssertionError(f"JWT-like pattern found in metric value: {line}")

    def test_metrics_no_database_credentials(self, client: TestClient):
        """Test that metrics do not expose database credentials."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for database credential patterns
        assert "mongodb://" not in content
        assert "postgresql://" not in content
        assert "redis://" not in content
        # Redis may or may not appear in metric names depending on what metrics are exposed
        # The critical check is that connection strings are not exposed

    def test_metrics_no_connection_strings(self, client: TestClient):
        """Test that metrics do not expose connection strings."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for connection string patterns
        assert "host=" not in content or "host" in "# HELP"
        assert "port=" not in content or "port" in "# HELP"
        assert "user=" not in content or "user" in "# HELP"  # Allow in comments

    def test_metrics_no_openai_keys(self, client: TestClient):
        """Test that metrics do not expose OpenAI API keys."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for OpenAI key patterns
        assert "sk-" not in content
        assert "openai" not in content or "openai" in "# TYPE" or "openai" in "# HELP"

    def test_metrics_no_google_keys(self, client: TestClient):
        """Test that metrics do not expose Google API keys."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for Google key patterns
        assert "aiza" not in content
        assert "google" not in content or "google" in "# TYPE" or "google" in "# HELP"

    def test_metrics_no_groq_keys(self, client: TestClient):
        """Test that metrics do not expose Groq API keys."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for Groq key patterns
        assert "gsk_" not in content
        # Groq may or may not be present in provider labels, but keys should never be exposed


class TestMetricsUserDataExposure:
    """Test that metrics do not expose user data."""

    def test_metrics_no_email_exposure(self, client: TestClient):
        """Test that metrics do not expose email addresses."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for email patterns
        assert "@" not in content or "@" in "# HELP" or "@" in "# TYPE"
        # Allow @ in metric names if needed (unlikely but possible)
        lines = content.split('\n')
        for line in lines:
            if '@' in line and not line.strip().startswith('#'):
                # Check if it's an email pattern
                if '@' in line and '.' in line.split('@')[-1][:10]:  # Basic email check
                    assert False, f"Possible email in metrics: {line}"

    def test_metrics_no_user_id_exposure(self, client: TestClient):
        """Test that metrics do not expose user IDs."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for user_id patterns
        # Allow "user_id" in comments or metric definitions
        lines = content.split('\n')
        for line in lines:
            if 'user_id' in line and not line.strip().startswith('#'):
                # user_id should not appear in metric values
                parts = line.split()
                if len(parts) > 1:
                    # Check if user_id is a label value (not label name)
                    labels_part = ' '.join(parts[1:])
                    if 'user_id="' in labels_part or "user_id='" in labels_part:
                        assert False, f"user_id used as label value: {line}"

    def test_metrics_no_username_exposure(self, client: TestClient):
        """Test that metrics do not expose usernames."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for username patterns
        assert "username" not in content or "username" in "# HELP" or "username" in "# TYPE"

    def test_metrics_no_personal_data(self, client: TestClient):
        """Test that metrics do not expose personal data."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for personal data patterns
        personal_terms = ["name", "address", "phone", "ssn", "social"]
        for term in personal_terms:
            # Allow in comments
            if term in content and term not in "# HELP" and term not in "# TYPE":
                # Check if it appears in data (not comments)
                lines = content.split('\n')
                for line in lines:
                    if term in line and not line.strip().startswith('#'):
                        # Conservative check - fail if personal term found in data
                        # This might be overly strict but ensures safety
                        if f'{term}="' in line or f"{term}='" in line:
                            assert False, f"Possible personal data in metrics: {line}"

    def test_metrics_no_journal_content(self, client: TestClient):
        """Test that metrics do not expose journal content."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for journal content patterns
        # Allow "journal" in metric names (e.g., http requests to /journals)
        lines = content.split('\n')
        for line in lines:
            if 'journal' in line and not line.strip().startswith('#'):
                # Journal should only be in URLs/routes, not content
                # This is a basic check
                if len(line) > 200:  # Unusually long line might contain content
                    assert False, f"Unusually long metric line (possible content): {line[:100]}"

    def test_metrics_no_document_content(self, client: TestClient):
        """Test that metrics do not expose document content."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for document content patterns
        lines = content.split('\n')
        for line in lines:
            if not line.strip().startswith('#'):
                # Check for unusually long values that might be content
                parts = line.split()
                if len(parts) > 1:
                    value = parts[-1]
                    if len(value) > 100:  # Unusually long value
                        assert False, f"Unusually long metric value (possible content): {line[:100]}"


class TestMetricsTenantIsolation:
    """Test that metrics do not expose tenant information."""

    def test_metrics_no_tenant_id_exposure(self, client: TestClient):
        """Test that metrics do not expose tenant IDs."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for tenant_id patterns
        assert "tenant_id" not in content or "tenant_id" in "# HELP" or "tenant_id" in "# TYPE"

    def test_metrics_no_organization_exposure(self, client: TestClient):
        """Test that metrics do not expose organization information."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for organization patterns
        assert "organization" not in content or "organization" in "# HELP" or "organization" in "# TYPE"
        assert "org_id" not in content or "org_id" in "# HELP" or "org_id" in "# TYPE"

    def test_metrics_no_workspace_exposure(self, client: TestClient):
        """Test that metrics do not expose workspace information."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for workspace patterns
        assert "workspace" not in content or "workspace" in "# HELP" or "workspace" in "# TYPE"
        assert "workspace_id" not in content or "workspace_id" in "# HELP" or "workspace_id" in "# TYPE"


class TestMetricsNetworkInformation:
    """Test that metrics do not expose network topology."""

    def test_metrics_no_ip_addresses(self, client: TestClient):
        """Test that metrics do not expose IP addresses."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for IP address patterns
        # This is a basic check - might have false positives
        lines = content.split('\n')
        for line in lines:
            if not line.strip().startswith('#'):
                # Check for IPv4 pattern
                import re
                ipv4_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
                if re.search(ipv4_pattern, line):
                    # Might be in URLs or other legitimate places
                    # But should not be in metric values
                    parts = line.split()
                    if len(parts) > 1:
                        value = parts[-1]
                        if re.match(ipv4_pattern, value):
                            assert False, f"IP address in metric value: {line}"

    def test_metrics_no_internal_urls(self, client: TestClient):
        """Test that metrics do not expose internal URLs."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for internal URL patterns
        # Allow localhost in development but check for internal IPs
        internal_patterns = ["192.168.", "10.", "172.16."]
        for pattern in internal_patterns:
            # Pattern might appear in comments
            if pattern in content:
                lines = content.split('\n')
                for line in lines:
                    if pattern in line and not line.strip().startswith('#'):
                        # Check if it's in a value (not a label name)
                        parts = line.split()
                        if len(parts) > 1 and pattern in parts[-1]:
                            assert False, f"Internal network pattern in metric value: {line}"

    def test_metrics_no_dns_names(self, client: TestClient):
        """Test that metrics do not expose internal DNS names."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for internal DNS patterns
        internal_dns = [".internal", ".local", ".corp", ".priv"]
        for pattern in internal_dns:
            # Pattern might appear in comments
            if pattern in content:
                lines = content.split('\n')
                for line in lines:
                    if pattern in line and not line.strip().startswith('#'):
                        # Check if it's in a value
                        parts = line.split()
                        if len(parts) > 1 and pattern in parts[-1]:
                            assert False, f"Internal DNS pattern in metric value: {line}"


class TestMetricsErrorMessages:
    """Test that metrics do not expose sensitive error messages."""

    def test_metrics_no_raw_exceptions(self, client: TestClient):
        """Test that metrics do not expose raw exception messages."""
        response = client.get("/v1/metrics")
        content = response.text.lower()

        # Check for exception patterns
        exception_patterns = ["exception", "error", "traceback", "stack trace"]
        for pattern in exception_patterns:
            # Allow in comments
            if pattern in content and pattern not in "# HELP" and pattern not in "# TYPE":
                # Check if it appears in data
                lines = content.split('\n')
                for line in lines:
                    if pattern in line and not line.strip().startswith('#'):
                        # Check if it's in a value (might be an error message)
                        parts = line.split()
                        if len(parts) > 1:
                            value = ' '.join(parts[1:])
                            if len(value) > 50:  # Long value might be an error message
                                assert False, f"Possible exception message in metrics: {line[:100]}"

    def test_metrics_no_stack_traces(self, client: TestClient):
        """Test that metrics do not expose stack traces."""
        response = client.get("/v1/metrics")
        content = response.text

        # Check for stack trace patterns
        stack_patterns = ["file \"/", "line ", "in function", "at line"]
        for pattern in stack_patterns:
            assert pattern not in content.lower()


class TestMetricsLabelSecurity:
    """Test that metric labels do not contain sensitive information."""

    def test_metric_labels_no_sensitive_terms(self, client: TestClient):
        """Test that metric labels do not contain sensitive terms."""
        response = client.get("/v1/metrics")
        content = response.text

        # Parse metrics to check labels
        lines = content.split('\n')
        sensitive_terms = ["password", "secret", "token", "key", "credential"]

        for line in lines:
            if line and not line.startswith('#'):
                # Check for sensitive terms in label values
                for term in sensitive_terms:
                    # Allow in metric names but not in label values
                    if term in line.lower():
                        # Check if it's a label value
                        if f'{term}="' in line.lower() or f"{term}='" in line.lower():
                            # If it's not a metric name (which comes first), it's a label
                            metric_name = line.split()[0] if line.split() else ""
                            if term not in metric_name.lower():
                                assert False, f"Sensitive term in label value: {line}"


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def app():
    """Create the FastAPI app for testing."""
    from app.main import app
    return app
