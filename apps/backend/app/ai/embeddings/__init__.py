# apps/backend/app/ai/embeddings/__init__.py
"""Embedding Provider Abstraction Layer."""

from .interface import (
    EmbeddingConfig,
    EmbeddingProviderAuthenticationError,
    EmbeddingProviderConnectionError,
    EmbeddingProviderError,
    EmbeddingProviderInterface,
)
from .providers import (
    CohereEmbeddingProvider,
    EmbeddingProviderFactory,
    FastEmbedEmbeddingProvider,
    MockEmbeddingProvider,
    OpenAIEmbeddingProvider,
    SentenceTransformersEmbeddingProvider,
)

__all__ = [
    "EmbeddingProviderInterface",
    "EmbeddingConfig",
    "EmbeddingProviderError",
    "EmbeddingProviderConnectionError",
    "EmbeddingProviderAuthenticationError",
    "OpenAIEmbeddingProvider",
    "CohereEmbeddingProvider",
    "FastEmbedEmbeddingProvider",
    "SentenceTransformersEmbeddingProvider",
    "MockEmbeddingProvider",
    "EmbeddingProviderFactory",
]
