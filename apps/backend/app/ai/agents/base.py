# apps/backend/app/ai/agents/base.py
"""
Base Agent Interface - Foundation for all AI agents.

This interface defines the contract that all specialized agents must implement,
ensuring consistency across the multi-agent system.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from ..llm.interface import LLMProviderInterface, LLMMessage

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Context information passed to agents during processing."""

    user_id: str
    conversation_history: List[Dict[str, str]]
    retrieved_memories: List[str]
    knowledge_context: Optional[str] = None
    user_preferences: Optional[Dict[str, Any]] = None
    current_state: Optional[Dict[str, Any]] = None


@dataclass
class AgentResponse:
    """Standardized response from agents."""

    content: str
    agent_type: str
    confidence: float
    tool_calls: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    follow_up_questions: Optional[List[str]] = None


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents.

    Each specialized agent (Fitness Coach, Habit Coach, etc.) must inherit
    from this class and implement the required methods.
    """

    def __init__(
        self,
        llm_provider: LLMProviderInterface,
        system_prompt: str,
        agent_type: str,
    ):
        self.llm_provider = llm_provider
        self.system_prompt = system_prompt
        self.agent_type = agent_type
        self._tools: Dict[str, callable] = {}

    @abstractmethod
    async def process(
        self,
        query: str,
        context: AgentContext,
    ) -> AgentResponse:
        """
        Process a user query and generate a response.

        Args:
            query: The user's query
            context: AgentContext with conversation history, memories, etc.

        Returns:
            AgentResponse with the agent's answer and metadata
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Return a description of what this agent does."""
        pass

    @abstractmethod
    def get_keywords(self) -> List[str]:
        """Return keywords for routing queries to this agent."""
        pass

    def register_tool(self, name: str, func: callable) -> None:
        """Register a tool that this agent can use."""
        self._tools[name] = func
        logger.info(f"Registered tool '{name}' for agent {self.agent_type}")

    async def _build_messages(
        self,
        query: str,
        context: AgentContext,
    ) -> List[LLMMessage]:
        """Build the message list for LLM generation."""
        messages = [LLMMessage(role="system", content=self.system_prompt)]

        # Add retrieved memories to system prompt
        if context.retrieved_memories:
            memories_text = "\n".join([f"- {mem}" for mem in context.retrieved_memories])
            memory_prompt = f"\n\nRelevant memories about this user:\n{memories_text}"
            messages[0].content += memory_prompt

        # Add knowledge context if available
        if context.knowledge_context:
            messages[0].content += f"\n\n{context.knowledge_context}"

        # Add conversation history
        for msg in context.conversation_history[-10:]:  # Last 10 turns
            messages.append(
                LLMMessage(role=msg.get("role", "user"), content=msg.get("content", ""))
            )

        # Add current query
        messages.append(LLMMessage(role="user", content=query))

        return messages

    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a registered tool."""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not registered for agent {self.agent_type}")

        tool_func = self._tools[tool_name]
        return await tool_func(**arguments)

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Return list of available tools for this agent."""
        return [
            {"name": name, "description": func.__doc__ or "No description"}
            for name, func in self._tools.items()
        ]


class AgentFactory:
    """Factory for creating agent instances."""

    _agents: Dict[str, type] = {}

    @classmethod
    def register(cls, agent_type: str, agent_class: type) -> None:
        """Register an agent class."""
        cls._agents[agent_type] = agent_class
        logger.info(f"Registered agent type: {agent_type}")

    @classmethod
    def create(cls, agent_type: str, **kwargs) -> BaseAgent:
        """Create an agent instance."""
        agent_class = cls._agents.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")

        return agent_class(**kwargs)

    @classmethod
    def list_agents(cls) -> List[str]:
        """Return list of registered agent types."""
        return list(cls._agents.keys())
