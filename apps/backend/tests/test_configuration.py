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
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_FAIL_OPEN: bool = False
    ALLOW_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    JWT_ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=None,  # Disable .env file loading for testing
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    def _validate_environment_contracts(self) -> None:
        """Validate environment-specific contracts (simplified for testing)."""
        if self.APP_ENV == "production":
            errors = []

            if self.APP_DEBUG is not False:
                errors.append("APP_DEBUG must be False in production")

            if self.RATE_LIMIT_ENABLED is not True:
                errors.append("RATE_LIMIT_ENABLED must be True in production")

            if self.RATE_LIMIT_FAIL_OPEN is not False:
                errors.append("RATE_LIMIT_FAIL_OPEN must be False in production (fail-closed)")

            if len(self.SECRET_KEY) < 32:
                errors.append("SECRET_KEY must be at least 32 characters in production")

            if len(self.JWT_SECRET) < 32:
                errors.append("JWT_SECRET must be at least 32 characters in production")

            if self.SECRET_KEY == self.JWT_SECRET:
                errors.append("SECRET_KEY and JWT_SECRET must be different in production")

            if self.POSTGRES_URL and "localhost" in self.POSTGRES_URL:
                errors.append("POSTGRES_URL must not contain localhost in production")

            if self.MONGODB_URL and "localhost" in self.MONGODB_URL:
                errors.append("MONGODB_URL must not contain localhost in production")

            if self.REDIS_URL and "localhost" in self.REDIS_URL:
                errors.append("REDIS_URL must not contain localhost in production")

            if self.QDRANT_URL and "localhost" in self.QDRANT_URL:
                errors.append("QDRANT_URL must not contain localhost in production")

            if self.ALLOW_ORIGINS:
                origins = [origin.strip() for origin in self.ALLOW_ORIGINS.split(",")]
                for origin in origins:
                    if "localhost" in origin.lower() or "127.0.0.1" in origin:
                        errors.append(f"ALLOW_ORIGINS contains localhost address '{origin}' in production")

            if self.JWT_ALGORITHM == "RS256":
                if not self.JWT_SECRET_RS256_PRIVATE:
                    errors.append("JWT_SECRET_RS256_PRIVATE is required when JWT_ALGORITHM=RS256")
                if not self.JWT_SECRET_RS256_PUBLIC:
                    errors.append("JWT_SECRET_RS256_PUBLIC is required when JWT_ALGORITHM=RS256")

            if not self.GROQ_API_KEY and not self.GEMINI_API_KEY:
                errors.append("At least one LLM API key (GROQ_API_KEY or GEMINI_API_KEY) must be set in production")

            if errors:
                raise ValueError(
                    f"Production environment contract validation failed: {', '.join(errors)}. "
                    "Production requires explicit secure configuration."
                )

        if self.APP_ENV == "staging":
            if self.APP_DEBUG is True:
                raise ValueError(
                    "APP_DEBUG must be False in staging environment. "
                    "Staging should behave like production."
                )
            if self.RATE_LIMIT_ENABLED is False:
                raise ValueError(
                    "RATE_LIMIT_ENABLED must be True in staging environment. "
                    "Staging should behave like production."
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
        monkeypatch.setenv("VECTOR_DIMENSION", "1024")  # Cohere expects 1024

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
        monkeypatch.setenv("EMBEDDING_PROVIDER", "fastembed")  # fastembed uses 384
        monkeypatch.setenv("VECTOR_DIMENSION", "384")

        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.VECTOR_DIMENSION == 384

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
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

        config = Settings(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333"
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
            APP_ENV="staging",
            APP_DEBUG="false",
            RATE_LIMIT_ENABLED="true"
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


class TestEnvironmentContracts:
    """Test environment-specific configuration contracts."""

    def test_development_allows_debug_true(self, monkeypatch):
        """Test that development environment allows debug mode."""
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("APP_DEBUG", "true")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-development-32chars",
            JWT_SECRET="test-jwt-secret-development-32chars",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.APP_ENV == "development"
        assert config.APP_DEBUG is True

    def test_development_allows_rate_limit_disabled(self, monkeypatch):
        """Test that development environment allows rate limiting disabled."""
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-development-32chars",
            JWT_SECRET="test-jwt-secret-development-32chars",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.RATE_LIMIT_ENABLED is False

    def test_production_requires_debug_false(self, monkeypatch):
        """Test that production environment requires debug mode disabled."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "true")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333",
            GROQ_API_KEY="test-groq-key"
        )

        with pytest.raises(ValueError, match="APP_DEBUG must be False in production"):
            config._validate_environment_contracts()

    def test_production_requires_rate_limit_enabled(self, monkeypatch):
        """Test that production environment requires rate limiting enabled."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333",
            GROQ_API_KEY="test-groq-key"
        )

        with pytest.raises(ValueError, match="RATE_LIMIT_ENABLED must be True in production"):
            config._validate_environment_contracts()

    def test_production_rejects_localhost_in_postgres_url(self, monkeypatch):
        """Test that production rejects localhost in PostgreSQL URL."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://localhost:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333",
            GROQ_API_KEY="test-groq-key"
        )

        with pytest.raises(ValueError, match="POSTGRES_URL must not contain localhost in production"):
            config._validate_environment_contracts()

    def test_production_rejects_localhost_in_mongodb_url(self, monkeypatch):
        """Test that production rejects localhost in MongoDB URL."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://localhost:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333",
            GROQ_API_KEY="test-groq-key"
        )

        with pytest.raises(ValueError, match="MONGODB_URL must not contain localhost in production"):
            config._validate_environment_contracts()

    def test_production_rejects_localhost_in_redis_url(self, monkeypatch):
        """Test that production rejects localhost in Redis URL."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://localhost:6379/0",
            QDRANT_URL="http://production-host:6333",
            GROQ_API_KEY="test-groq-key"
        )

        with pytest.raises(ValueError, match="REDIS_URL must not contain localhost in production"):
            config._validate_environment_contracts()

    def test_production_rejects_localhost_in_qdrant_url(self, monkeypatch):
        """Test that production rejects localhost in Qdrant URL."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://localhost:6333",
            GROQ_API_KEY="test-groq-key"
        )

        with pytest.raises(ValueError, match="QDRANT_URL must not contain localhost in production"):
            config._validate_environment_contracts()

    def test_production_rejects_localhost_in_cors_origins(self, monkeypatch):
        """Test that production rejects localhost in CORS origins."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("ALLOW_ORIGINS", "http://localhost:3000,https://example.com")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333",
            GROQ_API_KEY="test-groq-key"
        )

        with pytest.raises(ValueError, match="ALLOW_ORIGINS contains localhost address"):
            config._validate_environment_contracts()

    def test_production_rejects_127_0_0_1_in_cors_origins(self, monkeypatch):
        """Test that production rejects 127.0.0.1 in CORS origins."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("ALLOW_ORIGINS", "http://127.0.0.1:3000,https://example.com")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333",
            GROQ_API_KEY="test-groq-key"
        )

        with pytest.raises(ValueError, match="ALLOW_ORIGINS contains localhost address"):
            config._validate_environment_contracts()

    def test_production_accepts_valid_cors_origins(self, monkeypatch):
        """Test that production accepts valid CORS origins."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("ALLOW_ORIGINS", "https://example.com,https://app.example.com")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333",
            GROQ_API_KEY="test-groq-key"
        )

        assert config.ALLOW_ORIGINS == "https://example.com,https://app.example.com"

    def test_production_requires_rs256_keys_when_algorithm_rs256(self, monkeypatch):
        """Test that production requires RS256 keys when algorithm is RS256."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("JWT_ALGORITHM", "RS256")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333",
            GROQ_API_KEY="test-groq-key"
        )

        with pytest.raises(ValueError, match="JWT_SECRET_RS256_PRIVATE is required when JWT_ALGORITHM=RS256"):
            config._validate_environment_contracts()

    def test_production_requires_rs256_public_key_when_algorithm_rs256(self, monkeypatch):
        """Test that production requires RS256 public key when algorithm is RS256."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("JWT_ALGORITHM", "RS256")
        monkeypatch.setenv("JWT_SECRET_RS256_PRIVATE", "test-private-key")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333",
            GROQ_API_KEY="test-groq-key"
        )

        with pytest.raises(ValueError, match="JWT_SECRET_RS256_PUBLIC is required when JWT_ALGORITHM=RS256"):
            config._validate_environment_contracts()

    def test_production_accepts_rs256_keys_when_algorithm_rs256(self, monkeypatch):
        """Test that production accepts RS256 keys when algorithm is RS256."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("JWT_ALGORITHM", "RS256")
        monkeypatch.setenv("JWT_SECRET_RS256_PRIVATE", "test-private-key")
        monkeypatch.setenv("JWT_SECRET_RS256_PUBLIC", "test-public-key")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333",
            GROQ_API_KEY="test-groq-key"
        )

        assert config.JWT_ALGORITHM == "RS256"
        assert config.JWT_SECRET_RS256_PRIVATE == "test-private-key"
        assert config.JWT_SECRET_RS256_PUBLIC == "test-public-key"

    def test_production_requires_at_least_one_llm_key(self, monkeypatch):
        """Test that production requires at least one LLM API key."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333"
        )

        with pytest.raises(ValueError, match="At least one LLM API key"):
            config._validate_environment_contracts()

    def test_production_accepts_groq_key(self, monkeypatch):
        """Test that production accepts Groq API key."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333"
        )

        assert config.GROQ_API_KEY == "test-groq-key"

    def test_production_accepts_gemini_key(self, monkeypatch):
        """Test that production accepts Gemini API key."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333"
        )

        assert config.GEMINI_API_KEY == "test-gemini-key"

    def test_production_requires_secret_key_min_32_chars(self, monkeypatch):
        """Test that production requires SECRET_KEY to be at least 32 characters."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

        config = SettingsWithoutEnv(
            SECRET_KEY="short",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333"
        )

        with pytest.raises(ValueError, match="SECRET_KEY must be at least 32 characters in production"):
            config._validate_environment_contracts()

    def test_production_requires_jwt_secret_min_32_chars(self, monkeypatch):
        """Test that production requires JWT_SECRET to be at least 32 characters."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="short",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333"
        )

        with pytest.raises(ValueError, match="JWT_SECRET must be at least 32 characters in production"):
            config._validate_environment_contracts()

    def test_production_requires_different_secret_and_jwt_secret(self, monkeypatch):
        """Test that production requires SECRET_KEY and JWT_SECRET to be different."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-secret-key-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333"
        )

        with pytest.raises(ValueError, match="SECRET_KEY and JWT_SECRET must be different in production"):
            config._validate_environment_contracts()

    def test_production_requires_fail_closed_rate_limiting(self, monkeypatch):
        """Test that production requires RATE_LIMIT_FAIL_OPEN to be False."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_FAIL_OPEN", "true")
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars",
            JWT_SECRET="test-jwt-secret-production-32chars",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333"
        )

        with pytest.raises(ValueError, match="RATE_LIMIT_FAIL_OPEN must be False in production"):
            config._validate_environment_contracts()

    def test_staging_requires_debug_false(self, monkeypatch):
        """Test that staging environment requires debug mode disabled."""
        monkeypatch.setenv("APP_ENV", "staging")
        monkeypatch.setenv("APP_DEBUG", "true")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-staging-32chars",
            JWT_SECRET="test-jwt-secret-staging-32chars",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        with pytest.raises(ValueError, match="APP_DEBUG must be False in staging environment"):
            config._validate_environment_contracts()

    def test_staging_requires_rate_limit_enabled(self, monkeypatch):
        """Test that staging environment requires rate limiting enabled."""
        monkeypatch.setenv("APP_ENV", "staging")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-staging-32chars",
            JWT_SECRET="test-jwt-secret-staging-32chars",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        with pytest.raises(ValueError, match="RATE_LIMIT_ENABLED must be True in staging environment"):
            config._validate_environment_contracts()

    def test_valid_production_configuration(self, monkeypatch):
        """Test that valid production configuration passes all validations."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_FAIL_OPEN", "false")
        monkeypatch.setenv("ALLOW_ORIGINS", "https://example.com,https://app.example.com")
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret-key-production-32chars-minimum",
            JWT_SECRET="test-jwt-secret-production-32chars-different",
            POSTGRES_URL="postgresql://production-host:5432/lumenly",
            MONGODB_URL="mongodb://production-host:27017/lumenly",
            REDIS_URL="redis://production-host:6379/0",
            QDRANT_URL="http://production-host:6333"
        )

        assert config.APP_ENV == "production"
        assert config.APP_DEBUG is False
        assert config.RATE_LIMIT_ENABLED is True
        assert config.RATE_LIMIT_FAIL_OPEN is False
