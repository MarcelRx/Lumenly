# apps/backend/app/ai/orchestration/router.py
"""
AI Orchestration Router - Central routing and coordination for AI components.

This module provides:
- Intelligent routing between specialized agents
- Request/response orchestration
- Fallback and error handling
- Performance monitoring
"""
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..agents.base import AgentContext, AgentResponse, BaseAgent
from ..llm.interface import LLMProviderInterface
from ..memory_engine.manager import MemoryManager

try:
    from ..embeddings.interface import EmbeddingProviderInterface
except ImportError:
    EmbeddingProviderInterface = object  # Fallback for type hints

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Result of routing decision."""
    agent_type: str
    confidence: float
    reasoning: str


class AIOrchestrator:
    """
    Central orchestrator for AI request processing.

    Coordinates between:
    - Agent routing
    - Memory retrieval
    - Knowledge retrieval
    - LLM generation
    - Tool execution
    """

    def __init__(
        self,
        llm_provider: LLMProviderInterface,
        embedding_provider: Optional[EmbeddingProviderInterface] = None,
        memory_manager: Optional[MemoryManager] = None,
        enable_fallback: bool = True,
    ):
        self.llm_provider = llm_provider
        self.embedding_provider = embedding_provider
        self.memory_manager = memory_manager
        self.enable_fallback = enable_fallback
        self._agents: Dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the orchestrator."""
        self._agents[agent.agent_type] = agent
        logger.info(f"Registered agent: {agent.agent_type}")

    async def route_request(
        self,
        query: str,
        user_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> RoutingDecision:
        """
        Route a request to the appropriate agent.

        Args:
            query: User's query
            user_id: User identifier
            conversation_history: Optional conversation history for context

        Returns:
            RoutingDecision with selected agent and confidence
        """
        if conversation_history is None:
            conversation_history = []

        # Simple keyword-based routing (can be enhanced with ML)
        scores = {}
        for agent_type, agent in self._agents.items():
            keywords = agent.get_keywords()
            score = sum(1 for kw in keywords if kw.lower() in query.lower())
            scores[agent_type] = score

        # Find highest score
        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                best_agent = max(scores, key=scores.get)
                return RoutingDecision(
                    agent_type=best_agent,
                    confidence=min(max_score / 3.0, 1.0),  # Normalize
                    reasoning=f"Matched {max_score} keywords for {best_agent}",
                )

        # Default to first agent or generic fallback
        default_agent = next(iter(self._agents.keys()), "default")
        return RoutingDecision(
            agent_type=default_agent,
            confidence=0.5,
            reasoning="No clear match, using default agent",
        )

    async def process_request(
        self,
        query: str,
        user_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        enable_memory: bool = True,
    ) -> AgentResponse:
        """
        Process a complete AI request through the orchestration pipeline.

        Pipeline:
        1. Route to appropriate agent
        2. Retrieve memory context
        3. Process through agent
        4. Handle tool execution if needed
        5. Save conversation turn
        6. Return response

        Args:
            query: User's query
            user_id: User identifier
            conversation_history: Optional conversation history
            enable_memory: Whether to use memory retrieval

        Returns:
            AgentResponse with the final answer
        """
        try:
            # Step 1: Route request
            routing = await self.route_request(query, user_id, conversation_history)
            logger.info(f"Routed request to {routing.agent_type} (confidence: {routing.confidence})")

            # Step 2: Get agent
            agent = self._agents.get(routing.agent_type)
            if not agent:
                raise ValueError(f"Agent not found: {routing.agent_type}")

            # Step 3: Build context
            retrieved_memories = []
            if enable_memory and self.memory_manager:
                # Generate query embedding for memory retrieval
                try:
                    if self.embedding_provider:
                        query_embedding = await self.embedding_provider.embed(query)
                    else:
                        query_embedding = await self.llm_provider.generate_embedding(query)
                    retrieved_memories = await self.memory_manager.long_term.retrieve_relevant(
                        user_id=user_id,
                        query_vector=query_embedding,
                        top_k=3,
                    )
                except Exception as e:
                    logger.warning(f"Memory retrieval failed: {e}")

            # Get conversation history from memory manager if not provided
            if not conversation_history and self.memory_manager:
                conversation_history = await self.memory_manager.short_term.get_history(user_id)

            # Build agent context
            context = AgentContext(
                user_id=user_id,
                conversation_history=conversation_history,
                retrieved_memories=retrieved_memories,
            )

            # Step 4: Process through agent
            response = await agent.process(query, context)

            # Step 5: Save conversation turn
            if enable_memory and self.memory_manager:
                try:
                    await self.memory_manager.save_turn(
                        user_id=user_id,
                        user_query=query,
                        assistant_response=response.content,
                    )
                except Exception as e:
                    logger.warning(f"Failed to save conversation turn: {e}")

            return response

        except Exception as e:
            logger.error(f"Request processing failed: {e}", exc_info=True)

            if self.enable_fallback:
                # Return a safe fallback response
                return AgentResponse(
                    content="I apologize, but I encountered an error processing your request. Please try again.",
                    agent_type="fallback",
                    confidence=0.0,
                )
            raise

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all components."""
        health = {
            "llm_provider": await self.llm_provider.health_check(),
            "memory_manager": True,  # Memory manager doesn't have health check yet
        }

        for agent_type, agent in self._agents.items():
            health[f"agent_{agent_type}"] = True  # Agents don't have health check yet

        return health

    def get_registered_agents(self) -> List[str]:
        """Return list of registered agent types."""
        return list(self._agents.keys())
