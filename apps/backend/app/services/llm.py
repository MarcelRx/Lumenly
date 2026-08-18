# apps/backend/app/services/llm.py
import random
from typing import List, Protocol

from app.core.config import settings


class LLMServiceInterface(Protocol):
    """Interface for LLM services providing embedding and response generation."""

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate an embedding vector for the given text."""
        ...

    async def generate_response(self, prompt: str, context: str) -> str:
        """Generate a response based on the prompt and context."""
        ...


class MockLLMService:
    """Mock implementation of LLM service for testing."""

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate a mock embedding vector with configured dimension."""
        # Return a static or randomized list of floats with configured dimension
        return [random.random() for _ in range(settings.VECTOR_DIMENSION)]

    async def generate_response(self, prompt: str, context: str) -> str:
        """Generate a mock AI response."""
        return "This is a mocked AI response based on the provided context."
