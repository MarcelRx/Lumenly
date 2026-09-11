# apps/backend/app/ai/llm/interface.py
"""
LLM Provider Interface - Unified abstraction for multiple LLM providers.

This interface provides a clean way to switch between:
- OpenAI
- Anthropic
- Gemini
- Local models (Ollama)
- Groq

Without changing business logic.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, AsyncIterator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMMessage:
    """Standardized message format for all LLM providers."""

    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class LLMResponse:
    """Standardized response format for all LLM providers."""

    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    model: Optional[str] = None
    usage: Optional[Dict[str, int]] = None  # tokens, etc.


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""

    provider: str  # "openai", "anthropic", "gemini", "groq", "ollama"
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # For local models or custom endpoints
    temperature: float = 0.7
    max_tokens: int = 1024
    timeout: int = 30
    max_retries: int = 3


class LLMProviderInterface(ABC):
    """
    Abstract interface for LLM providers.

    All providers must implement these methods to ensure
    consistent behavior across different LLM backends.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the LLM client (validate connection, etc.)."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            messages: Conversation history
            tools: Optional tool definitions for function calling
            tool_choice: Tool choice strategy ("auto", "none", or specific tool)

        Returns:
            LLMResponse with content, tool_calls, and metadata
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from the LLM.

        Yields content chunks as they are generated.
        """
        pass

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM provider is accessible and healthy."""
        pass

    async def close(self) -> None:
        """Clean up resources."""
        if self._client:
            # Provider-specific cleanup
            pass


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""

    pass


class LLMProviderConnectionError(LLMProviderError):
    """Raised when connection to LLM provider fails."""

    pass


class LLMProviderAuthenticationError(LLMProviderError):
    """Raised when authentication with LLM provider fails."""

    pass


class LLMProviderRateLimitError(LLMProviderError):
    """Raised when rate limit is exceeded."""

    pass


class LLMProviderTimeoutError(LLMProviderError):
    """Raised when LLM request times out."""

    pass
