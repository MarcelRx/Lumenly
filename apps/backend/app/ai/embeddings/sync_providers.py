# apps/backend/app/ai/embeddings/sync_providers.py
"""
Synchronous Embedding Provider Implementations for Celery Workers.

These implementations provide synchronous embedding generation for use in
Celery workers without creating event loops or using asyncio.run().
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SyncEmbeddingConfig:
    """Configuration for synchronous embedding providers."""

    provider: str  # "openai", "cohere", "fastembed", "sentence_transformers"
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    dimension: Optional[int] = None  # Expected embedding dimension
    batch_size: int = 32


class SyncEmbeddingProviderInterface:
    """
    Abstract interface for synchronous embedding providers.

    All providers must implement these methods to ensure
    consistent behavior across different embedding backends.
    """

    def __init__(self, config: SyncEmbeddingConfig):
        self.config = config
        self._client = None

    def initialize(self) -> None:
        """Initialize the embedding provider (load models, validate connection, etc.)."""
        pass

    def embed(self, text: str) -> List[float]:
        """
        Generate an embedding vector for a single text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        raise NotImplementedError

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embedding vectors for multiple texts efficiently.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors (list of float lists)
        """
        raise NotImplementedError

    def get_dimension(self) -> int:
        """Return the dimension of the embedding vectors."""
        raise NotImplementedError

    def health_check(self) -> bool:
        """Check if the embedding provider is accessible and healthy."""
        return True

    def close(self) -> None:
        """Clean up resources."""
        if self._client:
            # Provider-specific cleanup
            pass


class SyncOpenAIEmbeddingProvider(SyncEmbeddingProviderInterface):
    """Synchronous OpenAI embeddings API provider implementation."""

    def initialize(self) -> None:
        try:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
            logger.info(
                f"Sync OpenAI embedding provider initialized with model: {self.config.model}"
            )
        except ImportError:
            raise ImportError("openai package not installed")
        except Exception as e:
            raise ConnectionError(f"Failed to initialize OpenAI client: {e}")

    def embed(self, text: str) -> List[float]:
        try:
            response = self._client.embeddings.create(
                model=self.config.model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            self._handle_error(e)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            response = self._client.embeddings.create(
                model=self.config.model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            self._handle_error(e)

    def get_dimension(self) -> int:
        """Return the dimension of the embedding vectors."""
        if self.config.dimension:
            return self.config.dimension

        # Default dimensions for OpenAI models
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return model_dimensions.get(self.config.model, 1536)

    def health_check(self) -> bool:
        try:
            self._client.embeddings.create(
                model=self.config.model,
                input="test",
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI embedding health check failed: {e}")
            return False

    def _handle_error(self, error: Exception) -> None:
        """Convert OpenAI errors to our standard exceptions."""
        from openai import APIConnectionError, AuthenticationError, RateLimitError

        if isinstance(error, AuthenticationError):
            raise PermissionError(str(error))
        elif isinstance(error, RateLimitError):
            raise RuntimeError(f"Rate limit exceeded: {error}")
        elif isinstance(error, APIConnectionError):
            raise ConnectionError(str(error))
        else:
            raise RuntimeError(f"OpenAI embedding error: {error}")


class SyncCohereEmbeddingProvider(SyncEmbeddingProviderInterface):
    """Synchronous Cohere embeddings API provider implementation."""

    def initialize(self) -> None:
        try:
            import cohere

            self._client = cohere.Client(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
            logger.info(
                f"Sync Cohere embedding provider initialized with model: {self.config.model}"
            )
        except ImportError:
            raise ImportError("cohere package not installed")
        except Exception as e:
            raise ConnectionError(f"Failed to initialize Cohere client: {e}")

    def embed(self, text: str) -> List[float]:
        try:
            response = self._client.embed(
                texts=[text],
                model=self.config.model,
                input_type="search_document",
            )
            return response.embeddings[0]
        except Exception as e:
            self._handle_error(e)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            response = self._client.embed(
                texts=texts,
                model=self.config.model,
                input_type="search_document",
                batch_size=self.config.batch_size,
            )
            return response.embeddings
        except Exception as e:
            self._handle_error(e)

    def get_dimension(self) -> int:
        """Return the dimension of the embedding vectors."""
        if self.config.dimension:
            return self.config.dimension

        # Default dimensions for Cohere models
        model_dimensions = {
            "embed-english-v3.0": 1024,
            "embed-english-light-v3.0": 384,
            "embed-multilingual-v3.0": 1024,
            "embed-multilingual-light-v3.0": 384,
        }
        return model_dimensions.get(self.config.model, 1024)

    def health_check(self) -> bool:
        try:
            self._client.embed(
                texts=["test"],
                model=self.config.model,
            )
            return True
        except Exception as e:
            logger.error(f"Cohere embedding health check failed: {e}")
            return False

    def _handle_error(self, error: Exception) -> None:
        """Convert Cohere errors to our standard exceptions."""
        import cohere

        if isinstance(error, cohere.errors.UnauthorizedError):
            raise PermissionError(str(error))
        elif isinstance(error, cohere.errors.RateLimitError):
            raise RuntimeError(f"Rate limit exceeded: {error}")
        elif isinstance(error, cohere.errors.ServiceUnavailableError):
            raise ConnectionError(str(error))
        else:
            raise RuntimeError(f"Cohere embedding error: {error}")


class SyncFastEmbedEmbeddingProvider(SyncEmbeddingProviderInterface):
    """Synchronous FastEmbed local embedding provider implementation."""

    def initialize(self) -> None:
        try:
            from fastembed import TextEmbedding

            self._client = TextEmbedding(model_name=self.config.model)
            logger.info(f"Sync FastEmbed provider initialized with model: {self.config.model}")
        except ImportError:
            raise ImportError("fastembed package not installed")
        except Exception as e:
            raise ConnectionError(f"Failed to initialize FastEmbed: {e}")

    def embed(self, text: str) -> List[float]:
        try:
            # FastEmbed is already synchronous
            embedding = list(self._client.embed([text]))[0]
            return embedding
        except Exception as e:
            raise RuntimeError(f"FastEmbed error: {e}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            embeddings = list(self._client.embed(texts, batch_size=self.config.batch_size))
            return embeddings
        except Exception as e:
            raise RuntimeError(f"FastEmbed error: {e}")

    def get_dimension(self) -> int:
        """Return the dimension of the embedding vectors."""
        if self.config.dimension:
            return self.config.dimension

        # Default dimensions for FastEmbed models
        model_dimensions = {
            "BAAI/bge-small-en-v1.5": 384,
            "BAAI/bge-base-en-v1.5": 768,
            "BAAI/bge-large-en-v1.5": 1024,
            "sentence-transformers/all-MiniLM-L6-v2": 384,
        }
        return model_dimensions.get(self.config.model, 384)

    def health_check(self) -> bool:
        try:
            list(self._client.embed(["test"]))
            return True
        except Exception as e:
            logger.error(f"FastEmbed health check failed: {e}")
            return False


class SyncSentenceTransformersEmbeddingProvider(SyncEmbeddingProviderInterface):
    """Synchronous SentenceTransformers local embedding provider implementation."""

    def initialize(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer

            self._client = SentenceTransformer(self.config.model)
            logger.info(
                f"Sync SentenceTransformers provider initialized with model: {self.config.model}"
            )
        except ImportError:
            raise ImportError("sentence-transformers package not installed")
        except Exception as e:
            raise ConnectionError(f"Failed to initialize SentenceTransformers: {e}")

    def embed(self, text: str) -> List[float]:
        try:
            embedding = self._client.encode(text, convert_to_numpy=False)
            return embedding.tolist()
        except Exception as e:
            raise RuntimeError(f"SentenceTransformers error: {e}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            embeddings = self._client.encode(texts, convert_to_numpy=False)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            raise RuntimeError(f"SentenceTransformers error: {e}")

    def get_dimension(self) -> int:
        """Return the dimension of the embedding vectors."""
        if self.config.dimension:
            return self.config.dimension

        # Default dimensions for SentenceTransformers models
        model_dimensions = {
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "paraphrase-MiniLM-L6-v2": 384,
        }
        return model_dimensions.get(self.config.model, 384)

    def health_check(self) -> bool:
        try:
            self._client.encode("test")
            return True
        except Exception as e:
            logger.error(f"SentenceTransformers health check failed: {e}")
            return False


class SyncMockEmbeddingProvider(SyncEmbeddingProviderInterface):
    """Mock embedding provider for testing and development."""

    def initialize(self) -> None:
        logger.info("Sync Mock embedding provider initialized")
        # No initialization needed for mock

    def embed(self, text: str) -> List[float]:
        """Generate a deterministic mock embedding based on text hash."""
        # Create a deterministic but pseudo-random embedding based on text
        import hashlib

        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)

        # Use configured dimension or default to 1536 (OpenAI default)
        dimension = self.config.dimension or 1536

        # Generate deterministic vector
        embedding = []
        for i in range(dimension):
            # Use hash to generate consistent values between 0 and 1
            val = ((hash_val >> (i % 32)) & 0xFF) / 255.0
            embedding.append(val)

        return embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings for multiple texts."""
        return [self.embed(text) for text in texts]

    def get_dimension(self) -> int:
        """Return the dimension of the embedding vectors."""
        return self.config.dimension or 1536

    def health_check(self) -> bool:
        """Mock provider is always healthy."""
        return True


class SyncEmbeddingProviderFactory:
    """Factory for creating synchronous embedding provider instances."""

    _providers = {
        "openai": SyncOpenAIEmbeddingProvider,
        "cohere": SyncCohereEmbeddingProvider,
        "fastembed": SyncFastEmbedEmbeddingProvider,
        "sentence_transformers": SyncSentenceTransformersEmbeddingProvider,
        "mock": SyncMockEmbeddingProvider,
    }

    @classmethod
    def create(cls, config: SyncEmbeddingConfig) -> SyncEmbeddingProviderInterface:
        """Create a synchronous embedding provider instance based on config."""
        provider_class = cls._providers.get(config.provider.lower())
        if not provider_class:
            raise ValueError(f"Unknown provider: {config.provider}")

        return provider_class(config)

    @classmethod
    def register_provider(cls, name: str, provider_class: type) -> None:
        """Register a custom provider."""
        cls._providers[name.lower()] = provider_class
