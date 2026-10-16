# apps/backend/app/core/config.py
import os
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Build the path to the .env file.
# This assumes the .env file is in the apps/backend/ directory.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_FILE_PATH = os.path.join(BASE_DIR, ".env")


class Settings(BaseSettings):
    # Application Config
    APP_ENV: Literal["development", "staging", "production", "test"] = "development"
    APP_NAME: str = "Lumenly"
    VERSION: str = "0.1.0"
    APP_DEBUG: bool = True
    SECRET_KEY: str = Field(
        ...,
        description="Application secret key - REQUIRED in production",
    )

    # Known placeholder/test secrets that must be rejected in production
    _PLACEHOLDER_SECRETS = {
        "test_secret_key_do_not_use_in_production",
        "test_jwt_secret_do_not_use_in_production",
        "test_groq_api_key_replace_before_production",
        "test_gemini_api_key_replace_before_production",
        "test_elevenlabs_api_key_replace_before_production",
        "lumenly",  # Default database password
        "change_me_in_production",
        "generate-strong-secret-key-in-production",
        "generate-strong-jwt-secret-in-production",
        "mock-key",
    }

    def _is_placeholder_secret(self, value: str) -> bool:
        """Check if a value is a known placeholder/test secret."""
        if not value:
            return False
        value_lower = value.lower().strip()
        # Check for exact matches with known placeholders
        if value_lower in self._PLACEHOLDER_SECRETS:
            return True
        # Check for common test patterns
        if "test_" in value_lower and len(value_lower) < 50:
            return True
        if "replace_before_production" in value_lower:
            return True
        if "do_not_use_in_production" in value_lower:
            return True
        return False

    def _validate_production_secrets(self) -> None:
        """Validate that production doesn't use placeholder/test secrets."""
        if self.APP_ENV != "production":
            return

        errors = []

        # Check SECRET_KEY
        if self._is_placeholder_secret(self.SECRET_KEY):
            errors.append("SECRET_KEY appears to be a placeholder/test value")

        # Check JWT_SECRET
        if self._is_placeholder_secret(self.JWT_SECRET):
            errors.append("JWT_SECRET appears to be a placeholder/test value")

        # Check LLM API keys
        if self.GROQ_API_KEY and self._is_placeholder_secret(self.GROQ_API_KEY):
            errors.append("GROQ_API_KEY appears to be a placeholder/test value")

        if self.GEMINI_API_KEY and self._is_placeholder_secret(self.GEMINI_API_KEY):
            errors.append("GEMINI_API_KEY appears to be a placeholder/test value")

        # Check database credentials in URLs
        from urllib.parse import urlparse

        # Extract and check PostgreSQL password
        if self.POSTGRES_URL:
            try:
                parsed = urlparse(self.POSTGRES_URL)
                if parsed.password and self._is_placeholder_secret(parsed.password):
                    errors.append("POSTGRES_URL contains placeholder password")
            except Exception:
                pass

        # Extract and check MongoDB password
        if self.MONGODB_URL:
            try:
                parsed = urlparse(self.MONGODB_URL)
                if parsed.password and self._is_placeholder_secret(parsed.password):
                    errors.append("MONGODB_URL contains placeholder password")
            except Exception:
                pass

        # Extract and check Redis password
        if self.REDIS_URL:
            try:
                parsed = urlparse(self.REDIS_URL)
                if parsed.password and self._is_placeholder_secret(parsed.password):
                    errors.append("REDIS_URL contains placeholder password")
            except Exception:
                pass

        if errors:
            raise ValueError(
                f"Production configuration validation failed: {', '.join(errors)}. "
                "Replace placeholder/test secrets with real production values."
            )

    def _validate_environment_contracts(self) -> None:
        """Validate environment-specific configuration contracts."""
        if self.APP_ENV == "development":
            # Development allows most things, but should warn about obvious issues
            if self.APP_DEBUG is False:
                import warnings

                warnings.warn(
                    "APP_DEBUG is False in development environment. "
                    "This may make debugging difficult.",
                    RuntimeWarning,
                )
            return

        if self.APP_ENV == "test":
            # Test environment should be deterministic
            # No strict validation needed for test
            return

        if self.APP_ENV == "staging":
            # Staging should behave like production
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
            return

        if self.APP_ENV == "production":
            # Production has strict requirements
            errors = []

            # APP_DEBUG must be False
            if self.APP_DEBUG is not False:
                errors.append("APP_DEBUG must be False in production")

            # RATE_LIMIT_ENABLED must be True
            if self.RATE_LIMIT_ENABLED is not True:
                errors.append("RATE_LIMIT_ENABLED must be True in production")

            # RATE_LIMIT_FAIL_OPEN must be False
            if self.RATE_LIMIT_FAIL_OPEN is not False:
                errors.append("RATE_LIMIT_FAIL_OPEN must be False in production (fail-closed)")

            # Secret key length validation
            if len(self.SECRET_KEY) < 32:
                errors.append("SECRET_KEY must be at least 32 characters in production")

            if len(self.JWT_SECRET) < 32:
                errors.append("JWT_SECRET must be at least 32 characters in production")

            # SECRET_KEY and JWT_SECRET must be different
            if self.SECRET_KEY == self.JWT_SECRET:
                errors.append("SECRET_KEY and JWT_SECRET must be different in production")

            # Check for localhost in infrastructure URLs

            if self.POSTGRES_URL and "localhost" in self.POSTGRES_URL:
                errors.append("POSTGRES_URL must not contain localhost in production")

            if self.MONGODB_URL and "localhost" in self.MONGODB_URL:
                errors.append("MONGODB_URL must not contain localhost in production")

            if self.REDIS_URL and "localhost" in self.REDIS_URL:
                errors.append("REDIS_URL must not contain localhost in production")

            if self.QDRANT_URL and "localhost" in self.QDRANT_URL:
                errors.append("QDRANT_URL must not contain localhost in production")

            # Check CORS origins for localhost
            if self.ALLOW_ORIGINS:
                origins = [origin.strip() for origin in self.ALLOW_ORIGINS.split(",")]
                for origin in origins:
                    if "localhost" in origin.lower() or "127.0.0.1" in origin:
                        errors.append(
                            f"ALLOW_ORIGINS contains localhost address '{origin}' in production"
                        )

            # Check RS256 keys if algorithm is RS256
            if self.JWT_ALGORITHM == "RS256":
                if not self.JWT_SECRET_RS256_PRIVATE:
                    errors.append("JWT_SECRET_RS256_PRIVATE is required when JWT_ALGORITHM=RS256")
                if not self.JWT_SECRET_RS256_PUBLIC:
                    errors.append("JWT_SECRET_RS256_PUBLIC is required when JWT_ALGORITHM=RS256")

            # At least one LLM provider must be configured
            if not self.GROQ_API_KEY and not self.GEMINI_API_KEY:
                errors.append(
                    "At least one LLM API key (GROQ_API_KEY or GEMINI_API_KEY) must be set in production"
                )

            if errors:
                raise ValueError(
                    f"Production environment contract validation failed: {', '.join(errors)}. "
                    "Production requires explicit secure configuration."
                )

    # Infrastructure URLs
    POSTGRES_URL: str = Field(
        ...,
        description="PostgreSQL connection URL with credentials - REQUIRED",
    )
    MONGODB_URL: str = Field(
        ...,
        description="MongoDB connection URL - REQUIRED",
    )
    REDIS_URL: str = Field(
        ...,
        description="Redis connection URL - REQUIRED",
    )
    QDRANT_URL: str = Field(
        ...,
        description="Qdrant service URL - REQUIRED",
    )
    QDRANT_HOST: str = Field(
        default="localhost",
        description="Qdrant host",
    )
    QDRANT_PORT: int = Field(
        default=6333,
        description="Qdrant port",
    )
    QDRANT_API_KEY: Optional[str] = Field(
        default=None,
        description="Qdrant API key (optional for local instances)",
    )
    QDRANT_USE_HTTPS: bool = Field(
        default=False,
        description="Use HTTPS for Qdrant connection",
    )

    # LLM & Voice Providers
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    # Embedding Provider API Keys
    OPENAI_API_KEY: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None

    # Gemini model used for generateContent
    # Example: "gemini-2.5-flash", "gemini-3.5-flash"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_API_VERSION: str = "v1beta"

    ELEVENLABS_API_KEY: Optional[str] = None

    # Auth Config
    JWT_SECRET: str = Field(
        ...,
        description="Secret used to sign JWT access tokens - REQUIRED in production",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def ENVIRONMENT(self) -> str:
        return self.APP_ENV

    # RS256 Keys
    JWT_SECRET_RS256_PRIVATE: str = Field(
        default=None,
        description="RS256 private key for JWT signing (optional, for RS256 algorithm)",
    )
    JWT_SECRET_RS256_PUBLIC: str = Field(
        default=None,
        description="RS256 public key for JWT verification (optional, for RS256 algorithm)",
    )

    # CORS Configuration
    ALLOW_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated list of allowed CORS origins",
    )
    ALLOW_CREDENTIALS: bool = True
    ALLOW_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS,PATCH"
    ALLOW_HEADERS: str = "Content-Type,Authorization,X-Request-ID"

    # Embedding Configuration
    EMBEDDING_PROVIDER: str = Field(
        default="openai",
        description="Embedding provider: openai, cohere, fastembed, sentence_transformers",
    )
    EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name",
    )
    VECTOR_DIMENSION: int = Field(
        default=1536,
        description="Vector dimension for embeddings - must match embedding provider",
    )
    DISTANCE_METRIC: str = Field(
        default="Cosine",
        description="Distance metric for vector similarity: Cosine, Euclid, Dot",
    )

    def validate_embedding_config(self) -> None:
        """Validate that embedding configuration is consistent."""
        provider_dimensions = {
            "openai": 1536,  # text-embedding-3-small
            "cohere": 1024,  # embed-english-v3.0
            "fastembed": 384,  # BAAI/bge-small-en-v1.5
            "sentence_transformers": 384,  # all-MiniLM-L6-v2
        }

        expected_dimension = provider_dimensions.get(self.EMBEDDING_PROVIDER, 1536)

        if self.VECTOR_DIMENSION != expected_dimension:
            raise ValueError(
                f"Embedding provider '{self.EMBEDDING_PROVIDER}' expects vector dimension {expected_dimension}, "
                f"but VECTOR_DIMENSION is configured as {self.VECTOR_DIMENSION}. "
                f"Please update VECTOR_DIMENSION to match the embedding provider."
            )

        # Validate distance metric
        valid_metrics = ["Cosine", "Euclid", "Dot"]
        if self.DISTANCE_METRIC not in valid_metrics:
            raise ValueError(
                f"Invalid DISTANCE_METRIC '{self.DISTANCE_METRIC}'. "
                f"Must be one of: {', '.join(valid_metrics)}"
            )

    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REDIS_PREFIX: str = "rate_limit"
    RATE_LIMIT_ANONYMOUS_REQUESTS: int = Field(
        default=10,
        description="Max requests per minute for anonymous users",
    )
    RATE_LIMIT_AUTHENTICATED_REQUESTS: int = Field(
        default=100,
        description="Max requests per minute for authenticated users",
    )
    RATE_LIMIT_ADMIN_REQUESTS: int = Field(
        default=1000,
        description="Max requests per minute for admin users",
    )
    RATE_LIMIT_FAIL_OPEN: bool = Field(
        default=False,
        description="If False, block requests when Redis is unavailable (FAIL-CLOSED). If True, allow requests (FAIL-OPEN). Default FAIL-CLOSED for security.",
    )
    RATE_LIMIT_TRUSTED_PROXIES: str = Field(
        default="",
        description="Comma-separated list of trusted proxy IP addresses/CIDR ranges that can set X-Forwarded-For. Empty means no trusted proxies (ignore X-Forwarded-For).",
    )

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,  # <--- Use the explicit path here
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

# Run validation only in production/staging environments
# Development and test environments skip validation to allow flexible testing
if settings.APP_ENV in ["production", "staging"]:
    try:
        settings.validate_embedding_config()
        settings._validate_production_secrets()
        settings._validate_environment_contracts()
    except ValueError as e:
        raise ValueError(f"Configuration validation failed: {e}")
