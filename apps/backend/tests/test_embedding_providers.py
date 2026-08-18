# tests/test_embedding_providers.py
"""
Tests for Embedding Provider Interface and implementations.
"""
import pytest

from app.ai.embeddings.interface import (
    EmbeddingConfig,
    EmbeddingProviderAuthenticationError,
    EmbeddingProviderConnectionError,
    EmbeddingProviderError,
    EmbeddingProviderInterface,
)
from app.ai.embeddings.providers import (
    EmbeddingProviderFactory,
    MockEmbeddingProvider,
)


class TestEmbeddingConfig:
    """Test embedding configuration."""

    def test_embedding_config_creation(self):
        config = EmbeddingConfig(
            provider="openai",
            model="text-embedding-3-small",
            api_key="test-key",
            dimension=1536,
        )
        assert config.provider == "openai"
        assert config.model == "text-embedding-3-small"
        assert config.api_key == "test-key"
        assert config.dimension == 1536


class TestMockEmbeddingProvider:
    """Test mock embedding provider for testing."""

    @pytest.mark.asyncio
    async def test_mock_provider_initialization(self):
        config = EmbeddingConfig(provider="mock", model="mock-model")
        provider = MockEmbeddingProvider(config)
        await provider.initialize()
        assert provider._client == "mock"

    @pytest.mark.asyncio
    async def test_mock_provider_embed(self):
        from app.core.config import settings
        config = EmbeddingConfig(provider="mock", model="mock-model")
        provider = MockEmbeddingProvider(config)
        await provider.initialize()

        embedding = await provider.embed("Test text")
        assert len(embedding) == settings.VECTOR_DIMENSION
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_mock_provider_embed_batch(self):
        from app.core.config import settings
        config = EmbeddingConfig(provider="mock", model="mock-model")
        provider = MockEmbeddingProvider(config)
        await provider.initialize()

        texts = ["text1", "text2", "text3"]
        embeddings = await provider.embed_batch(texts)
        assert len(embeddings) == 3
        for embedding in embeddings:
            assert len(embedding) == settings.VECTOR_DIMENSION
            assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_mock_provider_get_dimension(self):
        from app.core.config import settings
        config = EmbeddingConfig(provider="mock", model="mock-model")
        provider = MockEmbeddingProvider(config)
        
        dimension = provider.get_dimension()
        assert dimension == settings.VECTOR_DIMENSION

    @pytest.mark.asyncio
    async def test_mock_provider_custom_dimension(self):
        config = EmbeddingConfig(provider="mock", model="mock-model", dimension=768)
        provider = MockEmbeddingProvider(config)
        
        dimension = provider.get_dimension()
        assert dimension == 768

    @pytest.mark.asyncio
    async def test_mock_provider_health_check(self):
        config = EmbeddingConfig(provider="mock", model="mock-model")
        provider = MockEmbeddingProvider(config)
        await provider.initialize()

        assert await provider.health_check() is True


class TestEmbeddingProviderFactory:
    """Test embedding provider factory."""

    def test_factory_create_mock_provider(self):
        config = EmbeddingConfig(provider="mock", model="mock-model")
        provider = EmbeddingProviderFactory.create(config)
        assert isinstance(provider, MockEmbeddingProvider)

    def test_factory_invalid_provider(self):
        config = EmbeddingConfig(provider="invalid", model="test")
        with pytest.raises(EmbeddingProviderError):
            EmbeddingProviderFactory.create(config)

    def test_factory_register_custom_provider(self):
        class CustomProvider(EmbeddingProviderInterface):
            async def initialize(self):
                pass
            async def embed(self, text):
                return [0.0] * 384
            async def embed_batch(self, texts):
                return [[0.0] * 384 for _ in texts]
            def get_dimension(self):
                return 384
            async def health_check(self):
                return True

        EmbeddingProviderFactory.register_provider("custom", CustomProvider)
        config = EmbeddingConfig(provider="custom", model="custom-model")
        provider = EmbeddingProviderFactory.create(config)
        assert isinstance(provider, CustomProvider)


class TestEmbeddingProviderErrors:
    """Test embedding provider error handling."""

    def test_embedding_provider_error(self):
        with pytest.raises(EmbeddingProviderError):
            raise EmbeddingProviderError("Test error")

    def test_embedding_provider_connection_error(self):
        with pytest.raises(EmbeddingProviderConnectionError):
            raise EmbeddingProviderConnectionError("Connection failed")

    def test_embedding_provider_authentication_error(self):
        with pytest.raises(EmbeddingProviderAuthenticationError):
            raise EmbeddingProviderAuthenticationError("Auth failed")


class TestDimensionConsistency:
    """Test dimension consistency across providers."""

    def test_mock_provider_dimension_matches_config(self):
        from app.core.config import settings
        config = EmbeddingConfig(provider="mock", model="mock-model")
        provider = MockEmbeddingProvider(config)
        
        # Mock provider should use settings.VECTOR_DIMENSION by default
        assert provider.get_dimension() == settings.VECTOR_DIMENSION

    def test_custom_dimension_overrides_config(self):
        config = EmbeddingConfig(provider="mock", model="mock-model", dimension=512)
        provider = MockEmbeddingProvider(config)
        
        # Custom dimension should override settings
        assert provider.get_dimension() == 512

    @pytest.mark.asyncio
    async def test_embedding_dimension_matches_config(self):
        from app.core.config import settings
        config = EmbeddingConfig(provider="mock", model="mock-model")
        provider = MockEmbeddingProvider(config)
        await provider.initialize()

        embedding = await provider.embed("test")
        assert len(embedding) == settings.VECTOR_DIMENSION


class TestProviderInterface:
    """Test that all providers implement the required interface."""

    @pytest.mark.asyncio
    async def test_mock_provider_implements_interface(self):
        config = EmbeddingConfig(provider="mock", model="mock-model")
        provider = MockEmbeddingProvider(config)
        
        # Verify all required methods exist
        assert hasattr(provider, 'initialize')
        assert hasattr(provider, 'embed')
        assert hasattr(provider, 'embed_batch')
        assert hasattr(provider, 'get_dimension')
        assert hasattr(provider, 'health_check')
        
        # Verify methods are callable
        assert callable(provider.initialize)
        assert callable(provider.embed)
        assert callable(provider.embed_batch)
        assert callable(provider.get_dimension)
        assert callable(provider.health_check)
