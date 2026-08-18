# apps/backend/app/ai/__init__.py
"""
AI Module - Central hub for all AI-related functionality.

This module provides:
- LLM provider abstraction
- Embedding services
- Agent system
- Memory management
- Knowledge retrieval
- Orchestration and routing
"""

from .agents.base import (
    AgentContext,
    AgentFactory,
    AgentResponse,
    BaseAgent,
)
from .embeddings.interface import (
    EmbeddingConfig,
    EmbeddingProviderError,
    EmbeddingProviderInterface,
)
from .llm.interface import (
    LLMConfig,
    LLMMessage,
    LLMProviderError,
    LLMProviderInterface,
    LLMResponse,
)
from .llm.providers import LLMProviderFactory
from .orchestration.router import AIOrchestrator, RoutingDecision

__all__ = [
    # LLM
    "LLMProviderInterface",
    "LLMConfig",
    "LLMMessage",
    "LLMResponse",
    "LLMProviderError",
    "LLMProviderFactory",
    # Embeddings
    "EmbeddingProviderInterface",
    "EmbeddingConfig",
    "EmbeddingProviderError",
    # Agents
    "BaseAgent",
    "AgentContext",
    "AgentResponse",
    "AgentFactory",
    # Orchestration
    "AIOrchestrator",
    "RoutingDecision",
]
