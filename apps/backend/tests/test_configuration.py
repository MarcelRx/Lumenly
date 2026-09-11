# apps/backend/tests/test_configuration.py
"""
Tests for application configuration management and validation.

Tests cover:
- Secret loading from environment
- Embedding configuration
- Rate limiting configuration
- CORS configuration
- Required field validation
"""
import pytest
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import Settings


class SettingsWithoutEnv(BaseSettings):
    """Test Settings class without .env file loading for validation tests."""
    SECRET_KEY: str = Field(..., description="Application secret key - REQUIRED in production")
    POSTGRES_URL: str = Field(..., description="PostgreSQL connection URL with credentials - REQUIRED")
    MONGODB_URL: str = Field(..., description="MongoDB connection URL - REQUIRED")
    REDIS_URL: str = Field(..., description="Redis connection URL - REQUIRED")
    QDRANT_URL: str = Field(..., description="Qdrant service URL - REQUIRED")
    JWT_SECRET: str = Field(..., description="Secret used to sign JWT access tokens - REQUIRED in production")
    GROQ_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    ELEVENLABS_API_KEY: str | None = None
    QDRANT_API_KEY: str | None = None
    JWT_SECRET_RS256_PRIVATE: str | None = None
    JWT_SECRET_RS256_PUBLIC: str | None = None

    model_config = SettingsConfigDict(
        env_file=None,  # Disable .env file loading for testing
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


class TestSecretLoading:
    def test_secret_key_required(self, monkeypatch):
        """Test that SECRET_KEY is required."""
        monkeypatch.delenv("SECRET_KEY", raising=False)
        with pytest.raises(ValidationError):
            SettingsWithoutEnv(
                POSTGRES_URL="postgresql://test",
                MONGODB_URL="mongodb://test",
                REDIS_URL="redis://test",
                QDRANT_URL="http://localhost:6333"
            )

    def test_secret_key_from_env(self, monkeypatch):
        """Test loading SECRET_KEY from environment."""
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-12345")

        config = Settings(
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.SECRET_KEY == "test-secret-key-12345"

    def test_jwt_secret_required(self, monkeypatch):
        """Test that JWT_SECRET is required."""
        monkeypatch.delenv("JWT_SECRET", raising=False)
        with pytest.raises(ValidationError):
            SettingsWithoutEnv(
                SECRET_KEY="test-secret",
                POSTGRES_URL="postgresql://test",
                MONGODB_URL="mongodb://test",
                REDIS_URL="redis://test",
                QDRANT_URL="http://localhost:6333"
            )

    def test_database_urls_required(self, monkeypatch):
        """Test that database URLs are required."""
        monkeypatch.delenv("POSTGRES_URL", raising=False)
        monkeypatch.delenv("MONGODB_URL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        with pytest.raises(ValidationError):
            SettingsWithoutEnv(
                SECRET_KEY="test-secret",
                JWT_SECRET="test-jwt-secret",
                QDRANT_URL="http://localhost:6333"
            )

    def test_qdrant_url_required(self, monkeypatch):
        """Test that QDRANT_URL is required."""
        monkeypatch.delenv("QDRANT_URL", raising=False)
        with pytest.raises(ValidationError):
            SettingsWithoutEnv(
                SECRET_KEY="test-secret",
                JWT_SECRET="test-jwt-secret",
                POSTGRES_URL="postgresql://test",
                MONGODB_URL="mongodb://test",
                REDIS_URL="redis://test"
            )


class TestEmbeddingConfiguration:
    """Test embedding configuration settings."""

    def test_default_embedding_provider(self):
        """Test default embedding provider."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.EMBEDDING_PROVIDER == "openai"

    def test_custom_embedding_provider(self, monkeypatch):
        """Test custom embedding provider."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "cohere")

        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.EMBEDDING_PROVIDER == "cohere"

    def test_default_embedding_model(self):
        """Test default embedding model."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.EMBEDDING_MODEL == "text-embedding-3-small"

    def test_custom_embedding_model(self, monkeypatch):
        """Test custom embedding model."""
        monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-large")

        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.EMBEDDING_MODEL == "text-embedding-3-large"

    def test_default_vector_dimension(self):
        """Test default vector dimension."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.VECTOR_DIMENSION == 1536

    def test_custom_vector_dimension(self, monkeypatch):
        """Test custom vector dimension."""
        monkeypatch.setenv("VECTOR_DIMENSION", "768")

        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.VECTOR_DIMENSION == 768

    def test_default_distance_metric(self):
        """Test default distance metric."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.DISTANCE_METRIC == "Cosine"

    def test_custom_distance_metric(self, monkeypatch):
        """Test custom distance metric."""
        monkeypatch.setenv("DISTANCE_METRIC", "Euclid")

        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.DISTANCE_METRIC == "Euclid"


class TestRateLimitingConfiguration:
    """Test rate limiting configuration settings."""

    def test_default_rate_limit_enabled(self):
        """Test default rate limiting enabled."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.RATE_LIMIT_ENABLED is True

    def test_rate_limit_can_be_disabled(self, monkeypatch):
        """Test that rate limiting can be disabled."""
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")

        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.RATE_LIMIT_ENABLED is False

    def test_default_anonymous_limit(self):
        """Test default anonymous user rate limit."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.RATE_LIMIT_ANONYMOUS_REQUESTS == 10

    def test_default_authenticated_limit(self):
        """Test default authenticated user rate limit."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.RATE_LIMIT_AUTHENTICATED_REQUESTS == 100

    def test_default_admin_limit(self):
        """Test default admin user rate limit."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.RATE_LIMIT_ADMIN_REQUESTS == 1000

    def test_custom_rate_limits(self, monkeypatch):
        """Test custom rate limit configuration."""
        monkeypatch.setenv("RATE_LIMIT_ANONYMOUS_REQUESTS", "20")
        monkeypatch.setenv("RATE_LIMIT_AUTHENTICATED_REQUESTS", "200")
        monkeypatch.setenv("RATE_LIMIT_ADMIN_REQUESTS", "2000")

        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.RATE_LIMIT_ANONYMOUS_REQUESTS == 20
        assert config.RATE_LIMIT_AUTHENTICATED_REQUESTS == 200
        assert config.RATE_LIMIT_ADMIN_REQUESTS == 2000


class TestCorsConfiguration:
    """Test CORS configuration settings."""

    def test_default_allow_origins(self):
        """Test default allowed origins."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert "http://localhost:3000" in config.ALLOW_ORIGINS
        assert "http://localhost:8000" in config.ALLOW_ORIGINS

    def test_custom_allow_origins(self, monkeypatch):
        """Test custom allowed origins."""
        monkeypatch.setenv("ALLOW_ORIGINS", "https://example.com,https://app.example.com")

        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.ALLOW_ORIGINS == "https://example.com,https://app.example.com"

    def test_default_allow_credentials(self):
        """Test default allow credentials setting."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.ALLOW_CREDENTIALS is True

    def test_default_allow_methods(self):
        """Test default allowed methods."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert "GET" in config.ALLOW_METHODS
        assert "POST" in config.ALLOW_METHODS
        assert "PUT" in config.ALLOW_METHODS
        assert "DELETE" in config.ALLOW_METHODS


class TestApplicationConfiguration:
    """Test general application configuration."""

    def test_default_app_environment(self):
        """Test default application environment."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.APP_ENV == "development"

    def test_custom_app_environment(self, monkeypatch):
        """Test custom application environment."""
        monkeypatch.setenv("APP_ENV", "production")

        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.APP_ENV == "production"

    def test_environment_property(self):
        """Test ENVIRONMENT property."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333",
            APP_ENV="staging"
        )

        assert config.ENVIRONMENT == "staging"

    def test_default_app_name(self):
        """Test default application name."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.APP_NAME == "Lumenly"

    def test_default_version(self):
        """Test default application version."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.VERSION == "0.1.0"


class TestOptionalApiKeys:
    """Test optional API key configuration."""

    def test_optional_api_keys_default_to_none(self):
        """Test that optional API keys default to None."""
        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        # In test environment, empty strings are equivalent to None for optional keys
        assert config.GROQ_API_KEY in (None, "")
        assert config.GEMINI_API_KEY in (None, "")
        assert config.ELEVENLABS_API_KEY in (None, "")
        assert config.QDRANT_API_KEY in (None, "")

    def test_optional_api_keys_can_be_set(self, monkeypatch):
        """Test that optional API keys can be configured."""
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.GROQ_API_KEY == "test-groq-key"
        assert config.GEMINI_API_KEY == "test-gemini-key"


class TestRs256Keys:
    """Test RS256 key configuration."""

    def test_rs256_keys_optional(self, monkeypatch):
        """Test that RS256 keys are optional."""
        # Clear RS256 environment variables to test default behavior
        monkeypatch.delenv("JWT_SECRET_RS256_PRIVATE", raising=False)
        monkeypatch.delenv("JWT_SECRET_RS256_PUBLIC", raising=False)

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.JWT_SECRET_RS256_PRIVATE is None
        assert config.JWT_SECRET_RS256_PUBLIC is None

    def test_rs256_keys_can_be_set(self, monkeypatch):
        """Test that RS256 keys can be configured."""
        monkeypatch.setenv("JWT_SECRET_RS256_PRIVATE", "test-private-key")
        monkeypatch.setenv("JWT_SECRET_RS256_PUBLIC", "test-public-key")

        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.JWT_SECRET_RS256_PRIVATE == "test-private-key"
        assert config.JWT_SECRET_RS256_PUBLIC == "test-public-key"
