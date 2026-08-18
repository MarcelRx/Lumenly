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
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_NAME: str = "Lumenly"
    VERSION: str = "0.1.0"
    APP_DEBUG: bool = True
    SECRET_KEY: str = Field(
        ...,
        description="Application secret key - REQUIRED in production",
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
            "cohere": 1024,   # embed-english-v3.0
            "fastembed": 384, # BAAI/bge-small-en-v1.5
            "sentence_transformers": 384, # all-MiniLM-L6-v2
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

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,  # <--- Use the explicit path here
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
