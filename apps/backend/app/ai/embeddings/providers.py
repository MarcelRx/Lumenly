# apps/backend/app/ai/embeddings/providers.py
"""
Embedding Provider Implementations.

Concrete implementations of EmbeddingProviderInterface for various providers.
"""

import logging
from typing import List

from .interface import (
    EmbeddingConfig,
    EmbeddingProviderAuthenticationError,
    EmbeddingProviderConnectionError,
    EmbeddingProviderError,
    EmbeddingProviderInterface,
)

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(EmbeddingProviderInterface):
    """OpenAI embeddings API provider implementation."""

    async def initialize(self) -> None:
        try:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
            logger.info(f"OpenAI embedding provider initialized with model: {self.config.model}")
        except ImportError:
            raise EmbeddingProviderError("openai package not installed")
        except Exception as e:
            raise EmbeddingProviderConnectionError(f"Failed to initialize OpenAI client: {e}")

    async def embed(self, text: str) -> List[float]:
        try:
            response = await self._client.embeddings.create(
                model=self.config.model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            self._handle_error(e)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            response = await self._client.embeddings.create(
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

    async def health_check(self) -> bool:
        try:
            await self._client.embeddings.create(
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
            raise EmbeddingProviderAuthenticationError(str(error))
        elif isinstance(error, RateLimitError):
            raise EmbeddingProviderError(f"Rate limit exceeded: {error}")
        elif isinstance(error, APIConnectionError):
            raise EmbeddingProviderConnectionError(str(error))
        else:
            raise EmbeddingProviderError(f"OpenAI embedding error: {error}")


class CohereEmbeddingProvider(EmbeddingProviderInterface):
    """Cohere embeddings API provider implementation."""

    async def initialize(self) -> None:
        try:
            import cohere

            self._client = cohere.AsyncClient(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
            logger.info(f"Cohere embedding provider initialized with model: {self.config.model}")
        except ImportError:
            raise EmbeddingProviderError("cohere package not installed")
        except Exception as e:
            raise EmbeddingProviderConnectionError(f"Failed to initialize Cohere client: {e}")

    async def embed(self, text: str) -> List[float]:
        try:
            response = await self._client.embed(
                texts=[text],
                model=self.config.model,
                input_type="search_document",
            )
            return response.embeddings[0]
        except Exception as e:
            self._handle_error(e)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            response = await self._client.embed(
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

    async def health_check(self) -> bool:
        try:
            await self._client.embed(
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
            raise EmbeddingProviderAuthenticationError(str(error))
        elif isinstance(error, cohere.errors.RateLimitError):
            raise EmbeddingProviderError(f"Rate limit exceeded: {error}")
        elif isinstance(error, cohere.errors.ServiceUnavailableError):
            raise EmbeddingProviderConnectionError(str(error))
        else:
            raise EmbeddingProviderError(f"Cohere embedding error: {error}")


class FastEmbedEmbeddingProvider(EmbeddingProviderInterface):
    """FastEmbed local embedding provider implementation."""

    async def initialize(self) -> None:
        try:
            from fastembed import TextEmbedding

            self._client = TextEmbedding(model_name=self.config.model)
            logger.info(f"FastEmbed provider initialized with model: {self.config.model}")
        except ImportError:
            raise EmbeddingProviderError("fastembed package not installed")
        except Exception as e:
            raise EmbeddingProviderConnectionError(f"Failed to initialize FastEmbed: {e}")

    async def embed(self, text: str) -> List[float]:
        try:
            # FastEmbed is synchronous, run in thread pool
            import asyncio

            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, lambda: list(self._client.embed([text]))[0]
            )
            return embedding
        except Exception as e:
            self._handle_error(e)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None, lambda: list(self._client.embed(texts, batch_size=self.config.batch_size))
            )
            return embeddings
        except Exception as e:
            self._handle_error(e)

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

    async def health_check(self) -> bool:
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: list(self._client.embed(["test"])))
            return True
        except Exception as e:
            logger.error(f"FastEmbed health check failed: {e}")
            return False

    def _handle_error(self, error: Exception) -> None:
        """Convert FastEmbed errors to our standard exceptions."""
        raise EmbeddingProviderError(f"FastEmbed error: {error}")


class SentenceTransformersEmbeddingProvider(EmbeddingProviderInterface):
    """SentenceTransformers local embedding provider implementation."""

    async def initialize(self) -> None:
        try:
            import asyncio

            from sentence_transformers import SentenceTransformer

            loop = asyncio.get_event_loop()
            self._client = await loop.run_in_executor(
                None, lambda: SentenceTransformer(self.config.model)
            )
            logger.info(
                f"SentenceTransformers provider initialized with model: {self.config.model}"
            )
        except ImportError:
            raise EmbeddingProviderError("sentence-transformers package not installed")
        except Exception as e:
            raise EmbeddingProviderConnectionError(
                f"Failed to initialize SentenceTransformers: {e}"
            )

    async def embed(self, text: str) -> List[float]:
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, lambda: self._client.encode(text, convert_to_numpy=False)
            )
            return embedding.tolist()
        except Exception as e:
            self._handle_error(e)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None, lambda: self._client.encode(texts, convert_to_numpy=False)
            )
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            self._handle_error(e)

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

    async def health_check(self) -> bool:
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self._client.encode("test"))
            return True
        except Exception as e:
            logger.error(f"SentenceTransformers health check failed: {e}")
            return False

    def _handle_error(self, error: Exception) -> None:
        """Convert SentenceTransformers errors to our standard exceptions."""
        raise EmbeddingProviderError(f"SentenceTransformers error: {error}")


class MockEmbeddingProvider(EmbeddingProviderInterface):
    """Mock embedding provider for testing and development."""

    async def initialize(self) -> None:
        logger.info("Mock embedding provider initialized")
        self._client = "mock"

    async def embed(self, text: str) -> List[float]:
        """Generate a deterministic mock embedding with configured dimension."""
        import hashlib

        # Use configured dimension, default to 1536 if not set
        dimension = self.config.dimension or 1536

        # Create a deterministic but pseudo-random embedding based on text
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)

        # Generate deterministic vector
        embedding = []
        for i in range(dimension):
            # Use hash to generate consistent values between 0 and 1
            val = ((hash_val >> (i % 32)) & 0xFF) / 255.0
            embedding.append(val)

        return embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings for multiple texts."""
        return [await self.embed(text) for text in texts]

    def get_dimension(self) -> int:
        """Return the configured dimension."""
        return self.config.dimension or 1536

    async def health_check(self) -> bool:
        return True


class EmbeddingProviderFactory:
    """Factory for creating embedding provider instances."""

    _providers = {
        "openai": OpenAIEmbeddingProvider,
        "cohere": CohereEmbeddingProvider,
        "fastembed": FastEmbedEmbeddingProvider,
        "sentence_transformers": SentenceTransformersEmbeddingProvider,
        "mock": MockEmbeddingProvider,
    }

    @classmethod
    def create(cls, config: EmbeddingConfig) -> EmbeddingProviderInterface:
        """Create an embedding provider instance based on config."""
        provider_class = cls._providers.get(config.provider.lower())
        if not provider_class:
            raise EmbeddingProviderError(f"Unknown provider: {config.provider}")

        return provider_class(config)

    @classmethod
    def register_provider(cls, name: str, provider_class: type) -> None:
        """Register a custom provider."""
        cls._providers[name.lower()] = provider_class
