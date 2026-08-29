# apps/backend/tests/test_secret_leakage_regression.py
"""
Secret leakage regression test for PHASE 10.1.

Ensures that sensitive values cannot accidentally appear in logs.
Tests representative values such as fake JWT, fake API key, fake password,
Authorization header, and database URL containing password.
"""
import logging
from io import StringIO

import pytest

from app.core.logging_config import SecretRedactingFormatter


class TestSecretLeakageRegression:
    """
    Regression tests to ensure sensitive values never appear in logs.

    Uses clearly synthetic test secrets only.
    """

    # Synthetic test secrets (clearly fake)
    FAKE_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake.synthetic.token.for.testing.only"
    FAKE_API_KEY = "sk-test-synthetic-api-key-12345-for-regression-testing"
    FAKE_PASSWORD = "TestPassword123!SyntheticForRegression"
    FAKE_AUTHORIZATION = f"Bearer {FAKE_JWT}"
    FAKE_DATABASE_URL = "postgresql://user:TestPassword123!@localhost:5432/db"
    FAKE_REDIS_URL = "redis://:TestPassword123!@localhost:6379/0"
    FAKE_MONGODB_URL = "mongodb://user:TestPassword123!@localhost:27017/db"
    FAKE_SECRET_KEY = "test-synthetic-secret-key-for-regression-testing-only"

    def setup_method(self):
        """Set up logging capture for each test."""
        # Create a string buffer to capture log output
        self.log_buffer = StringIO()
        self.handler = logging.StreamHandler(self.log_buffer)

        # Use the secret redacting formatter
        formatter = SecretRedactingFormatter()
        self.handler.setFormatter(formatter)

        # Set up a test logger
        self.logger = logging.getLogger("test_secret_leakage")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.handler)

    def teardown_method(self):
        """Clean up after each test."""
        self.logger.removeHandler(self.handler)
        self.handler.close()

    def get_log_output(self):
        """Get captured log output."""
        return self.log_buffer.getvalue()

    def test_fake_jwt_not_logged(self):
        """Test that fake JWT token does not appear in logs."""
        self.logger.info(f"Processing request with JWT: {self.FAKE_JWT}")

        log_output = self.get_log_output()

        # JWT should not appear in logs
        assert self.FAKE_JWT not in log_output, "JWT token appeared in logs"
        assert "eyJhbGci" not in log_output, "JWT token prefix appeared in logs"

        # Should be redacted
        assert "[REDACTED]" in log_output or "jwt=[REDACTED]" in log_output

    def test_fake_api_key_not_logged(self):
        """Test that fake API key does not appear in logs."""
        self.logger.info(f"api_key={self.FAKE_API_KEY}")

        log_output = self.get_log_output()

        # API key should not appear in logs
        assert self.FAKE_API_KEY not in log_output, "API key appeared in logs"
        assert "sk-test-synthetic" not in log_output, "API key prefix appeared in logs"

        # Should be redacted
        assert "[REDACTED]" in log_output or "api_key=[REDACTED]" in log_output

    def test_fake_password_not_logged(self):
        """Test that fake password does not appear in logs."""
        self.logger.info(f"password={self.FAKE_PASSWORD}")

        log_output = self.get_log_output()

        # Password should not appear in logs
        assert self.FAKE_PASSWORD not in log_output, "Password appeared in logs"
        assert "TestPassword123" not in log_output, "Password appeared in logs"

        # Should be redacted
        assert "[REDACTED]" in log_output or "password=[REDACTED]" in log_output

    def test_authorization_header_not_logged(self):
        """Test that Authorization header is not logged."""
        self.logger.info(f"Authorization: {self.FAKE_AUTHORIZATION}")

        log_output = self.get_log_output()

        # Authorization header should not appear in logs
        assert self.FAKE_AUTHORIZATION not in log_output, "Authorization header appeared in logs"
        assert "Bearer eyJhbGci" not in log_output, "Bearer token appeared in logs"

        # Should be redacted
        assert "[REDACTED]" in log_output or "Bearer [REDACTED]" in log_output

    def test_database_url_password_not_logged(self):
        """Test that database URL password is not logged."""
        self.logger.info(f"Database URL: {self.FAKE_DATABASE_URL}")

        log_output = self.get_log_output()

        # Database URL with password should not appear in logs
        assert self.FAKE_DATABASE_URL not in log_output, "Database URL with password appeared in logs"
        assert "TestPassword123" not in log_output, "Database password appeared in logs"

        # Password should be redacted
        assert "[REDACTED]" in log_output

    def test_redis_url_password_not_logged(self):
        """Test that Redis URL password is not logged."""
        self.logger.info(f"Redis URL: {self.FAKE_REDIS_URL}")

        log_output = self.get_log_output()

        # Redis URL with password should not appear in logs
        assert self.FAKE_REDIS_URL not in log_output, "Redis URL with password appeared in logs"
        assert "TestPassword123" not in log_output, "Redis password appeared in logs"

        # Password should be redacted
        assert "[REDACTED]" in log_output

    def test_mongodb_url_password_not_logged(self):
        """Test that MongoDB URL password is not logged."""
        self.logger.info(f"MongoDB URL: {self.FAKE_MONGODB_URL}")

        log_output = self.get_log_output()

        # MongoDB URL with password should not appear in logs
        assert self.FAKE_MONGODB_URL not in log_output, "MongoDB URL with password appeared in logs"
        assert "TestPassword123" not in log_output, "MongoDB password appeared in logs"

        # Password should be redacted
        assert "[REDACTED]" in log_output

    def test_secret_key_not_logged(self):
        """Test that secret key is not logged."""
        self.logger.info(f"secret={self.FAKE_SECRET_KEY}")

        log_output = self.get_log_output()

        # Secret key should not appear in logs
        assert self.FAKE_SECRET_KEY not in log_output, "Secret key appeared in logs"
        assert "test-synthetic-secret-key" not in log_output, "Secret key appeared in logs"

        # Should be redacted
        assert "[REDACTED]" in log_output or "secret=[REDACTED]" in log_output

    def test_multiple_secrets_in_single_log(self):
        """Test that multiple secrets in a single log are all redacted."""
        log_message = (
            f"JWT: {self.FAKE_JWT}, "
            f"API Key: {self.FAKE_API_KEY}, "
            f"Password: {self.FAKE_PASSWORD}"
        )
        self.logger.info(log_message)

        log_output = self.get_log_output()

        # None of the secrets should appear
        assert self.FAKE_JWT not in log_output
        assert self.FAKE_API_KEY not in log_output
        assert self.FAKE_PASSWORD not in log_output

        # All should be redacted
        assert log_output.count("[REDACTED]") >= 3

    def test_secret_in_error_log(self):
        """Test that secrets in error logs are redacted."""
        try:
            raise ValueError(f"Invalid API key: {self.FAKE_API_KEY}")
        except ValueError as e:
            self.logger.error(f"Error occurred: {e}", exc_info=True)

        log_output = self.get_log_output()

        # API key should not appear even in error logs
        assert self.FAKE_API_KEY not in log_output, "API key appeared in error log"

        # Should be redacted
        assert "[REDACTED]" in log_output

    def test_secret_in_warning_log(self):
        """Test that secrets in warning logs are redacted."""
        self.logger.warning(f"Suspicious activity with API key: {self.FAKE_API_KEY}")

        log_output = self.get_log_output()

        # API key should not appear in warning logs
        assert self.FAKE_API_KEY not in log_output, "API key appeared in warning log"

        # Should be redacted
        assert "[REDACTED]" in log_output

    def test_secret_in_debug_log(self):
        """Test that secrets in debug logs are redacted."""
        self.logger.debug(f"Debug info - password: {self.FAKE_PASSWORD}")

        log_output = self.get_log_output()

        # Password should not appear in debug logs
        assert self.FAKE_PASSWORD not in log_output, "Password appeared in debug log"

        # Should be redacted
        assert "[REDACTED]" in log_output

    def test_structured_logging_with_secrets(self):
        """Test that structured logging with extra fields redacts secrets."""
        self.logger.info(
            "Processing request",
            extra={
                "api_key": self.FAKE_API_KEY,
                "password": self.FAKE_PASSWORD,
                "authorization": self.FAKE_AUTHORIZATION
            }
        )

        log_output = self.get_log_output()

        # Secrets should not appear
        assert self.FAKE_API_KEY not in log_output
        assert self.FAKE_PASSWORD not in log_output
        assert self.FAKE_AUTHORIZATION not in log_output

    def test_case_insensitive_secret_patterns(self):
        """Test that secret patterns are caught case-insensitively."""
        # Test different case variations
        self.logger.info(f"PASSWORD={self.FAKE_PASSWORD}")
        self.logger.info(f"Api_Key={self.FAKE_API_KEY}")
        self.logger.info(f"JWT={self.FAKE_JWT}")

        log_output = self.get_log_output()

        # Secrets should not appear regardless of case
        assert self.FAKE_PASSWORD not in log_output
        assert self.FAKE_API_KEY not in log_output
        assert self.FAKE_JWT not in log_output

    def test_secret_with_common_variations(self):
        """Test that secrets with common naming variations are redacted."""
        variations = [
            f"token={self.FAKE_JWT}",
            f"access_token={self.FAKE_JWT}",
            f"auth_token={self.FAKE_JWT}",
            f"bearer_token={self.FAKE_JWT}",
        ]

        for variation in variations:
            self.logger.info(variation)

        log_output = self.get_log_output()

        # JWT should not appear in any variation
        assert self.FAKE_JWT not in log_output

    def test_log_sanitization_persistence(self):
        """Test that log sanitization works consistently across multiple logs."""
        for i in range(10):
            self.logger.info(f"Request {i} with API key: {self.FAKE_API_KEY}")

        log_output = self.get_log_output()

        # API key should not appear in any of the 10 logs
        assert self.FAKE_API_KEY not in log_output
        assert log_output.count("[REDACTED]") >= 10

    def test_concurrent_logging_with_secrets(self):
        """Test that concurrent logging with secrets is safe."""
        import threading

        def log_secret():
            for i in range(5):
                self.logger.info(f"Thread secret: {self.FAKE_PASSWORD}")

        threads = [threading.Thread(target=log_secret) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        log_output = self.get_log_output()

        # Password should not appear in any thread's logs
        assert self.FAKE_PASSWORD not in log_output


class TestSecretPatternsComprehensive:
    """
    Comprehensive tests for secret pattern detection.
    """

    def setup_method(self):
        """Set up logging capture for each test."""
        self.log_buffer = StringIO()
        self.handler = logging.StreamHandler(self.log_buffer)
        formatter = SecretRedactingFormatter()
        self.handler.setFormatter(formatter)

        self.logger = logging.getLogger("test_secret_patterns")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.handler)

    def teardown_method(self):
        """Clean up after each test."""
        self.logger.removeHandler(self.handler)
        self.handler.close()

    def get_log_output(self):
        """Get captured log output."""
        return self.log_buffer.getvalue()

    def test_password_pattern_variations(self):
        """Test various password pattern variations."""
        patterns = [
            "password=secret123",
            "Password=secret123",
            "PASSWORD=secret123",
            "password : secret123",
            "password:secret123",
        ]

        for pattern in patterns:
            self.logger.info(pattern)

        log_output = self.get_log_output()

        # None should contain the actual secret
        assert "secret123" not in log_output

    def test_api_key_pattern_variations(self):
        """Test various API key pattern variations."""
        patterns = [
            "api_key=sk-12345",
            "apiKey=sk-12345",
            "API_KEY=sk-12345",
            "api-key=sk-12345",
            "api key=sk-12345",
        ]

        for pattern in patterns:
            self.logger.info(pattern)

        log_output = self.get_log_output()

        # None should contain the actual key
        assert "sk-12345" not in log_output

    def test_token_pattern_variations(self):
        """Test various token pattern variations."""
        fake_token = "abc123def456"
        patterns = [
            f"token={fake_token}",
            f"Token={fake_token}",
            f"TOKEN={fake_token}",
            f"access_token={fake_token}",
            f"refresh_token={fake_token}",
        ]

        for pattern in patterns:
            self.logger.info(pattern)

        log_output = self.get_log_output()

        # None should contain the actual token
        assert fake_token not in log_output

    def test_secret_pattern_variations(self):
        """Test various secret pattern variations."""
        fake_secret = "my_secret_value"
        patterns = [
            f"secret={fake_secret}",
            f"Secret={fake_secret}",
            f"SECRET={fake_secret}",
            f"client_secret={fake_secret}",
            f"client_secret={fake_secret}",
        ]

        for pattern in patterns:
            self.logger.info(pattern)

        log_output = self.get_log_output()

        # None should contain the actual secret
        assert fake_secret not in log_output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
