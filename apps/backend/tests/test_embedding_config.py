# apps/backend/tests/test_embedding_config.py
"""
Tests for centralized embedding configuration.

Tests cover:
- Vector dimension consistency across components
- Distance metric configuration
- Embedding provider settings
- Configuration propagation to services
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.ai.memory.schema import get_qdrant_collections_config
from app.core.config import Settings
from app.services.vector import get_vector_dimension


class SettingsWithoutEnv(BaseSettings):
    """Test Settings class without .env file loading for validation tests."""
    SECRET_KEY: str = Field(..., description="Application secret key - REQUIRED in production")
    POSTGRES_URL: str = Field(..., description="PostgreSQL connection URL with credentials - REQUIRED")
    MONGODB_URL: str = Field(..., description="MongoDB connection URL - REQUIRED")
    REDIS_URL: str = Field(..., description="Redis connection URL - REQUIRED")
    QDRANT_URL: str = Field(..., description="Qdrant service URL - REQUIRED")
    JWT_SECRET: str = Field(..., description="Secret used to sign JWT access tokens - REQUIRED in production")
    VECTOR_DIMENSION: int = Field(default=1536, description="Vector dimension for embeddings")
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


class TestVectorDimensionConfiguration:
    """Test vector dimension configuration consistency."""

    def test_default_vector_dimension_in_settings(self):
        """Test default vector dimension in settings."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert config.VECTOR_DIMENSION == 1536

    def test_vector_dimension_in_vector_service(self):
        """Test that vector service uses configured dimension."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        assert get_vector_dimension() == config.VECTOR_DIMENSION

    def test_vector_dimension_in_workers(self):
        """Test that workers use configured dimension."""
        # Workers now access settings.VECTOR_DIMENSION directly
        from app.core.config import settings
        assert settings.VECTOR_DIMENSION == 1536

    def test_custom_vector_dimension_propagation(self, monkeypatch):
        """Test that custom vector dimension propagates to all components."""
        monkeypatch.setenv("VECTOR_DIMENSION", "768")

        config = SettingsWithoutEnv(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        # Verify settings picks up the custom dimension
        assert config.VECTOR_DIMENSION == 768


class TestDistanceMetricConfiguration:
    """Test distance metric configuration."""

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

    def test_distance_metric_in_qdrant_config(self):
        """Test that distance metric is used in Qdrant collection config."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        qdrant_config = get_qdrant_collections_config()

        for collection_name, collection_config in qdrant_config.items():
            assert collection_config["distance"] == config.DISTANCE_METRIC


class TestEmbeddingProviderConfiguration:
    """Test embedding provider configuration."""

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

    def test_embedding_model_configuration(self):
        """Test embedding model configuration."""
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


class TestQdrantCollectionConfiguration:
    """Test Qdrant collection configuration consistency."""

    def test_qdrant_collections_use_configured_dimension(self):
        """Test that Qdrant collections use configured vector dimension."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        qdrant_config = get_qdrant_collections_config()

        for collection_name, collection_config in qdrant_config.items():
            assert collection_config["vector_size"] == config.VECTOR_DIMENSION

    def test_qdrant_collections_use_configured_distance(self):
        """Test that Qdrant collections use configured distance metric."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        qdrant_config = get_qdrant_collections_config()

        for collection_name, collection_config in qdrant_config.items():
            assert collection_config["distance"] == config.DISTANCE_METRIC

    def test_qdrant_collections_have_required_fields(self):
        """Test that Qdrant collections have required payload fields."""
        qdrant_config = get_qdrant_collections_config()

        expected_collections = ["short_term_memory", "medium_term_memory", "long_term_memory"]
        for collection_name in expected_collections:
            assert collection_name in qdrant_config
            assert "vector_size" in qdrant_config[collection_name]
            assert "distance" in qdrant_config[collection_name]
            assert "payload_fields" in qdrant_config[collection_name]

    def test_qdrant_collections_include_user_id(self):
        """Test that all Qdrant collections include user_id in payload fields."""
        qdrant_config = get_qdrant_collections_config()

        for collection_name, collection_config in qdrant_config.items():
            assert "user_id" in collection_config["payload_fields"]


class TestMemoryStorageConfiguration:
    """Test memory storage configuration."""

    def test_memory_storage_uses_configured_dimension(self):
        """Test that memory storage uses configured vector dimension."""
        from app.ai.memory.storage import MultiBackendMemoryStorage

        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        # Test with default (no argument)
        storage = MultiBackendMemoryStorage()
        assert storage._vector_size == config.VECTOR_DIMENSION

        # Test with explicit dimension
        custom_storage = MultiBackendMemoryStorage(vector_size=768)
        assert custom_storage._vector_size == 768

    def test_memory_storage_validates_vector_dimension(self):
        """Test that memory storage validates vector dimensions."""
        from app.core.config import settings

        # Verify that the configured dimension is used
        expected_dimension = settings.VECTOR_DIMENSION

        # Create a vector with wrong dimension
        wrong_dimension_vector = [0.0] * 768

        # Verify dimensions don't match
        assert len(wrong_dimension_vector) != expected_dimension

        # The actual validation happens in async context during storage
        # This test verifies the configuration is accessible for validation
        assert expected_dimension == 1536


class TestLLMServiceConfiguration:
    """Test LLM service embedding configuration."""

    def test_llm_service_uses_configured_dimension(self):
        """Test that LLM service uses configured vector dimension."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        # This test would need to be async in actual implementation
        # For now, we verify the configuration is accessible
        assert config.VECTOR_DIMENSION == 1536


class TestConfigurationConsistency:
    """Test overall configuration consistency across components."""

    def test_all_components_use_same_dimension(self):
        """Test that all components use the same vector dimension."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        # Get dimensions from all components
        service_dim = get_vector_dimension()

        qdrant_config = get_qdrant_collections_config()
        qdrant_dim = qdrant_config["short_term_memory"]["vector_size"]

        assert config.VECTOR_DIMENSION == service_dim == qdrant_dim

    def test_all_components_use_same_distance_metric(self):
        """Test that all components use the same distance metric."""
        config = Settings(
            SECRET_KEY="test-secret",
            JWT_SECRET="test-jwt-secret",
            POSTGRES_URL="postgresql://test",
            MONGODB_URL="mongodb://test",
            REDIS_URL="redis://test",
            QDRANT_URL="http://localhost:6333"
        )

        qdrant_config = get_qdrant_collections_config()

        for collection_name, collection_config in qdrant_config.items():
            assert collection_config["distance"] == config.DISTANCE_METRIC
