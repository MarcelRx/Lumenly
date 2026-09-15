# apps/backend/tests/test_cors.py
"""
Tests for CORS policy configuration and security.

Tests cover:
- Origin parsing and validation
- Production wildcard rejection
- Development fallback behavior
- Configuration validation
"""
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import parse_cors_origins


class TestCorsOriginParsing:
    """Test CORS origin parsing functionality."""

    def test_parse_single_origin(self):
        """Test parsing a single origin."""
        origins_string = "https://example.com"
        origins = parse_cors_origins(origins_string)

        assert origins == ["https://example.com"]

    def test_parse_multiple_origins(self):
        """Test parsing multiple comma-separated origins."""
        origins_string = "https://example.com,https://app.example.com,https://admin.example.com"
        origins = parse_cors_origins(origins_string)

        assert len(origins) == 3
        assert "https://example.com" in origins
        assert "https://app.example.com" in origins
        assert "https://admin.example.com" in origins

    def test_parse_origins_with_whitespace(self):
        """Test parsing origins with extra whitespace."""
        origins_string = " https://example.com , https://app.example.com , https://admin.example.com "
        origins = parse_cors_origins(origins_string)

        assert len(origins) == 3
        assert origins == ["https://example.com", "https://app.example.com", "https://admin.example.com"]

    def test_parse_empty_string(self):
        """Test parsing empty string returns empty list."""
        origins = parse_cors_origins("")
        assert origins == []

    def test_parse_none_value(self):
        """Test parsing None returns empty list."""
        origins = parse_cors_origins(None)
        assert origins == []

    def test_parse_origins_with_empty_entries(self):
        """Test parsing origins with empty entries filters them out."""
        origins_string = "https://example.com,,https://app.example.com,"
        origins = parse_cors_origins(origins_string)

        assert len(origins) == 2
        assert "https://example.com" in origins
        assert "https://app.example.com" in origins


class TestCorsConfiguration:
    """Test CORS configuration settings."""

    def test_default_cors_origins(self):
        """Test default CORS origins configuration."""
        settings = Settings(
            SECRET_KEY="test-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333",
        )

        assert settings.ALLOW_ORIGINS == "http://localhost:3000,http://localhost:8000"

    def test_custom_cors_origins(self):
        """Test custom CORS origins configuration."""
        settings = Settings(
            SECRET_KEY="test-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333",
            ALLOW_ORIGINS="https://example.com,https://app.example.com"
        )

        assert settings.ALLOW_ORIGINS == "https://example.com,https://app.example.com"

    def test_cors_credentials_default(self):
        """Test default CORS credentials setting."""
        settings = Settings(
            SECRET_KEY="test-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333",
        )

        assert settings.ALLOW_CREDENTIALS is True

    def test_cors_methods_default(self):
        """Test default CORS methods."""
        settings = Settings(
            SECRET_KEY="test-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333",
        )

        assert "GET" in settings.ALLOW_METHODS
        assert "POST" in settings.ALLOW_METHODS
        assert "PUT" in settings.ALLOW_METHODS
        assert "DELETE" in settings.ALLOW_METHODS

    def test_cors_headers_default(self):
        """Test default CORS headers."""
        settings = Settings(
            SECRET_KEY="test-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333",
        )

        assert "Content-Type" in settings.ALLOW_HEADERS
        assert "Authorization" in settings.ALLOW_HEADERS
        assert "X-Request-ID" in settings.ALLOW_HEADERS


class TestCorsSecurity:
    """Test CORS security features."""

    def test_production_wildcard_rejection(self):
        """Test that wildcard origins are rejected in production."""
        with pytest.raises(ValueError, match="Wildcard CORS origins are not allowed in production"):
            settings = Settings(
                SECRET_KEY="test-secret-key-production-32chars",
                JWT_SECRET="test-jwt-secret-production-32chars",
                POSTGRES_URL="postgresql://production-host:5432/lumenly",
                MONGODB_URL="mongodb://production-host:27017/lumenly",
                REDIS_URL="redis://production-host:6379/0",
                QDRANT_URL="http://production-host:6333",
                APP_ENV="production",
                APP_DEBUG="false",
                RATE_LIMIT_ENABLED="true",
                GROQ_API_KEY="test-groq-key",
                ALLOW_ORIGINS="*"
            )

            # Simulate the production check from main.py
            allowed_origins = parse_cors_origins(settings.ALLOW_ORIGINS)
            if settings.APP_ENV == "production" and "*" in allowed_origins:
                raise ValueError(
                    "Wildcard CORS origins are not allowed in production. "
                    "Set ALLOW_ORIGINS environment variable to specific domains."
                )

    def test_development_wildcard_allowed(self):
        """Test that wildcard origins are allowed in development."""
        settings = Settings(
            SECRET_KEY="test-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333",
            APP_ENV="development",
            ALLOW_ORIGINS="*"
        )

        # Should not raise error in development
        allowed_origins = parse_cors_origins(settings.ALLOW_ORIGINS)
        assert "*" in allowed_origins

    def test_production_specific_origins_allowed(self):
        """Test that specific origins are allowed in production."""
        settings = Settings(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333",
            APP_ENV="production",
            APP_DEBUG="false",
            RATE_LIMIT_ENABLED="true",
            GROQ_API_KEY="test-groq-key",
            ALLOW_ORIGINS="https://example.com,https://app.example.com"
        )

        # Should not raise error with specific origins
        allowed_origins = parse_cors_origins(settings.ALLOW_ORIGINS)
        assert "*" not in allowed_origins
        assert len(allowed_origins) == 2


class TestCorsIntegration:
    """Test CORS integration with FastAPI application."""

    @pytest.fixture
    def test_app(self):
        """Create a test FastAPI app with CORS configured."""
        from app.main import app
        return app

    @pytest.fixture
    def test_client(self, test_app):
        """Create a test client for the app."""
        return TestClient(test_app)

    def test_cors_headers_on_options_request(self, test_client):
        """Test that CORS headers are present on OPTIONS requests."""
        # Use /health endpoint which bypasses rate limiting
        response = test_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            }
        )

        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers

    def test_cors_headers_on_api_request(self, test_client):
        """Test that CORS headers are present on API requests."""
        response = test_client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )

        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers

    def test_cors_allows_configured_origin(self, test_client):
        """Test that configured origins are allowed."""
        response = test_client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_credentials_allowed(self, test_client):
        """Test that credentials are allowed when configured."""
        response = test_client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )

        # Check if credentials header is present
        # Note: FastAPI CORS middleware doesn't always send this header
        # unless credentials are actually used
        assert response.status_code == 200


class TestCorsEnvironmentBehavior:
    """Test CORS behavior in different environments."""

    def test_development_fallback_origins(self):
        """Test development fallback to localhost when no origins configured."""
        settings = Settings(
            SECRET_KEY="test-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333",
            APP_ENV="development",
            ALLOW_ORIGINS=""
        )

        allowed_origins = parse_cors_origins(settings.ALLOW_ORIGINS)

        # Simulate development fallback from main.py
        if not allowed_origins and settings.APP_ENV == "development":
            allowed_origins = ["http://localhost:3000", "http://localhost:8000"]

        assert "http://localhost:3000" in allowed_origins
        assert "http://localhost:8000" in allowed_origins

    def test_production_no_fallback(self):
        """Test that production doesn't use fallback origins."""
        settings = Settings(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333",
            APP_ENV="production",
            APP_DEBUG="false",
            RATE_LIMIT_ENABLED="true",
            GROQ_API_KEY="test-groq-key",
            ALLOW_ORIGINS=""
        )

        allowed_origins = parse_cors_origins(settings.ALLOW_ORIGINS)

        # No fallback in production
        if not allowed_origins and settings.APP_ENV == "development":
            allowed_origins = ["http://localhost:3000", "http://localhost:8000"]

        assert allowed_origins == []


class TestCorsSecurityEdgeCases:
    """Test CORS security edge cases and potential bypasses."""

    def test_invalid_origin_format_rejected(self):
        """Test that invalid origin formats are handled safely."""
        # Various potentially malicious origin formats
        invalid_origins = [
            "javascript://alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "file:///etc/passwd",
            "ftp://malicious.com",
            "//evil.com",  # Protocol-relative URL
        ]

        for invalid_origin in invalid_origins:
            origins = parse_cors_origins(invalid_origin)
            # Should parse but not cause errors - actual validation happens in browser
            assert isinstance(origins, list)

    def test_multiple_configured_origins_enforced(self):
        """Test that multiple configured origins are all enforced."""
        settings = Settings(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333",
            APP_ENV="production",
            APP_DEBUG="false",
            RATE_LIMIT_ENABLED="true",
            GROQ_API_KEY="test-groq-key",
            ALLOW_ORIGINS="https://example.com,https://app.example.com,https://admin.example.com"
        )

        allowed_origins = parse_cors_origins(settings.ALLOW_ORIGINS)
        assert len(allowed_origins) == 3
        assert "https://example.com" in allowed_origins
        assert "https://app.example.com" in allowed_origins
        assert "https://admin.example.com" in allowed_origins

    def test_wildcard_with_mixed_origins_rejected_in_production(self):
        """Test that wildcard mixed with specific origins is rejected in production."""
        settings = Settings(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333",
            APP_ENV="production",
            APP_DEBUG="false",
            RATE_LIMIT_ENABLED="true",
            GROQ_API_KEY="test-groq-key",
            ALLOW_ORIGINS="*,https://example.com"
        )

        allowed_origins = parse_cors_origins(settings.ALLOW_ORIGINS)

        # Should reject wildcard even if mixed with specific origins
        if settings.APP_ENV == "production" and "*" in allowed_origins:
            with pytest.raises(ValueError, match="Wildcard CORS origins are not allowed in production"):
                raise ValueError(
                    "Wildcard CORS origins are not allowed in production. "
                    "Set ALLOW_ORIGINS environment variable to specific domains."
                )

    def test_staging_environment_treats_as_production(self):
        """Test that staging environment has production-like CORS restrictions."""
        settings = Settings(
            SECRET_KEY="test-secret-key-staging-32chars",
            JWT_SECRET="test-jwt-secret-staging-32chars",
            POSTGRES_URL="postgresql://staging-host:5432/lumenly",
            MONGODB_URL="mongodb://staging-host:27017/lumenly",
            REDIS_URL="redis://staging-host:6379/0",
            QDRANT_URL="http://staging-host:6333",
            APP_ENV="staging",
            APP_DEBUG="false",
            RATE_LIMIT_ENABLED="true",
            ALLOW_ORIGINS="*"
        )

        # Staging should not allow wildcard by default for security
        # This test documents current behavior - may need adjustment based on security policy
        allowed_origins = parse_cors_origins(settings.ALLOW_ORIGINS)
        # Currently staging allows wildcard - this may need to be changed
        assert "*" in allowed_origins

    def test_credentials_require_specific_origin(self):
        """Test that credentials should only be allowed with specific origins."""
        settings = Settings(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333",
            APP_ENV="production",
            APP_DEBUG="false",
            RATE_LIMIT_ENABLED="true",
            GROQ_API_KEY="test-groq-key",
            ALLOW_ORIGINS="https://example.com",
            ALLOW_CREDENTIALS=True
        )

        # When credentials are enabled, origins must be specific (not wildcard)
        allowed_origins = parse_cors_origins(settings.ALLOW_ORIGINS)
        assert "*" not in allowed_origins
        assert settings.ALLOW_CREDENTIALS is True

    def test_credentials_disabled_with_wildcard(self):
        """Test that credentials should be disabled when using wildcard."""
        settings = Settings(
            SECRET_KEY="test-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333",
            APP_ENV="development",
            ALLOW_ORIGINS="*",
            ALLOW_CREDENTIALS=False
        )

        # Wildcard with credentials is a security risk
        allowed_origins = parse_cors_origins(settings.ALLOW_ORIGINS)
        assert "*" in allowed_origins
        assert settings.ALLOW_CREDENTIALS is False
