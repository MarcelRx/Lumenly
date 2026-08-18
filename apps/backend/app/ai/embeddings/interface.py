# apps/backend/app/ai/embeddings/interface.py
"""
Embedding Provider Interface - Unified abstraction for embedding models.

This interface provides a clean way to switch between:
- OpenAI embeddings
- Cohere embeddings
- Local models (SentenceTransformers, FastEmbed)
- Custom embedding services

Without changing business logic.
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingConfig:
    """Configuration for embedding providers."""
    provider: str  # "openai", "cohere", "fastembed", "sentence_transformers"
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    dimension: Optional[int] = None  # Expected embedding dimension
    batch_size: int = 32


class EmbeddingProviderInterface(ABC):
    """
    Abstract interface for embedding providers.
    
    All providers must implement these methods to ensure
    consistent behavior across different embedding backends.
    """

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self._client = None

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the embedding provider (load models, validate connection, etc.)."""
        pass

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """
        Generate an embedding vector for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embedding vectors for multiple texts efficiently.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embedding vectors (list of float lists)
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Return the dimension of the embedding vectors."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the embedding provider is accessible and healthy."""
        pass

    async def close(self) -> None:
        """Clean up resources."""
        if self._client:
            # Provider-specific cleanup
            pass


class EmbeddingProviderError(Exception):
    """Base exception for embedding provider errors."""
    pass


class EmbeddingProviderConnectionError(EmbeddingProviderError):
    """Raised when connection to embedding provider fails."""
    pass


class EmbeddingProviderAuthenticationError(EmbeddingProviderError):
    """Raised when authentication with embedding provider fails."""
    pass
