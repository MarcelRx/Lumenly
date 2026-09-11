# apps/backend/app/ai/rag/orchestrator.py
"""
RAG Orchestrator - Unified Retrieval-Augmented Generation pipeline.

This module provides a production-quality RAG pipeline that integrates:
- Memory retrieval (short-term and long-term)
- Knowledge retrieval (document chunks)
- Vector search with tenant isolation
- Context construction and ranking
- LLM generation
- Security validation
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.ai.embeddings.interface import EmbeddingProviderInterface
from app.ai.knowledge_brain.retriever import KnowledgeRetriever
from app.ai.llm.interface import LLMMessage, LLMProviderInterface
from app.ai.memory_engine import MemoryManager
from app.ai.security import AISecurityValidator, SecurityConfig

logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    """Context gathered for RAG generation."""

    user_id: str
    query: str
    query_embedding: List[float]
    short_term_memory: List[Dict[str, str]]
    long_term_memories: List[str]
    knowledge_chunks: List[Dict[str, Any]]
    system_prompt: str
    security_context: Optional[Dict[str, Any]] = None


@dataclass
class RAGResponse:
    """Response from RAG pipeline."""

    content: str
    context_used: Dict[str, Any]
    retrieval_stats: Dict[str, int]
    security_validation: Dict[str, bool]
    metadata: Optional[Dict[str, Any]] = None


class RAGOrchestrator:
    """
    Unified RAG orchestrator for production-quality retrieval-augmented generation.

    Pipeline:
    1. Security validation
    2. Query embedding generation
    3. Memory retrieval (short-term + long-term)
    4. Knowledge retrieval
    5. Context construction and ranking
    6. LLM generation
    7. Response validation
    8. Memory persistence
    """

    def __init__(
        self,
        llm_provider: LLMProviderInterface,
        embedding_provider: EmbeddingProviderInterface,
        memory_manager: MemoryManager,
        knowledge_retriever: Optional[KnowledgeRetriever] = None,
        security_validator: Optional[AISecurityValidator] = None,
        max_context_chunks: int = 5,
        min_score_threshold: float = 0.65,
    ):
        self.llm_provider = llm_provider
        self.embedding_provider = embedding_provider
        self.memory_manager = memory_manager
        self.knowledge_retriever = knowledge_retriever
        self.security_validator = security_validator or AISecurityValidator(
            SecurityConfig(enable_user_isolation=True)
        )
        self.max_context_chunks = max_context_chunks
        self.min_score_threshold = min_score_threshold

    async def process_query(
        self,
        user_id: str,
        query: str,
        enable_memory: bool = True,
        enable_knowledge: bool = True,
    ) -> RAGResponse:
        """
        Process a user query through the complete RAG pipeline.

        Args:
            user_id: User identifier for tenant isolation
            query: User's query
            enable_memory: Whether to retrieve memory context
            enable_knowledge: Whether to retrieve knowledge context

        Returns:
            RAGResponse with generated content and metadata
        """
        try:
            # Step 1: Security validation
            security_result = await self._validate_request(user_id, query)

            # Step 2: Generate query embedding
            query_embedding = await self.embedding_provider.embed(query)

            # Step 3: Retrieve context
            context = await self._retrieve_context(
                user_id=user_id,
                query=query,
                query_embedding=query_embedding,
                enable_memory=enable_memory,
                enable_knowledge=enable_knowledge,
            )

            # Step 4: Build messages for LLM
            messages = self._build_messages(query, context)

            # Step 5: Generate response
            llm_response = await self.llm_provider.generate(messages)

            # Step 6: Validate response
            validated_content = self._validate_response(llm_response.content)

            # Step 7: Persist conversation turn
            if enable_memory:
                await self.memory_manager.save_turn(
                    user_id=user_id,
                    user_query=query,
                    assistant_response=validated_content,
                )

            # Build response
            return RAGResponse(
                content=validated_content,
                context_used={
                    "short_term_messages": len(context.short_term_memory),
                    "long_term_memories": len(context.long_term_memories),
                    "knowledge_chunks": len(context.knowledge_chunks),
                },
                retrieval_stats={
                    "total_context_items": (
                        len(context.short_term_memory)
                        + len(context.long_term_memories)
                        + len(context.knowledge_chunks)
                    ),
                },
                security_validation=security_result,
                metadata={
                    "model": llm_response.model,
                    "usage": llm_response.usage,
                },
            )

        except Exception as e:
            logger.error(f"RAG pipeline failed for user {user_id}: {e}", exc_info=True)
            raise

    async def _validate_request(
        self,
        user_id: str,
        query: str,
    ) -> Dict[str, bool]:
        """Validate request for security."""
        validation_results = {}

        # Validate user access (self-access is always valid)
        validation_results["user_access"] = self.security_validator.validate_user_access(
            user_id, user_id
        )

        # Detect prompt injection
        is_injection, reason = self.security_validator.detect_prompt_injection(query)
        validation_results["prompt_injection_detected"] = is_injection
        if is_injection:
            logger.warning(f"Prompt injection detected for user {user_id}: {reason}")

        # Sanitize input
        sanitized_query = self.security_validator.sanitize_input(query)
        validation_results["input_sanitized"] = sanitized_query != query

        return validation_results

    async def _retrieve_context(
        self,
        user_id: str,
        query: str,
        query_embedding: List[float],
        enable_memory: bool,
        enable_knowledge: bool,
    ) -> RAGContext:
        """Retrieve all relevant context for the query."""
        # Short-term memory
        short_term_memory = []
        if enable_memory:
            short_term_memory = await self.memory_manager.short_term.get_history(user_id)

        # Long-term memory
        long_term_memories = []
        if enable_memory:
            long_term_memories = await self.memory_manager.long_term.retrieve_relevant(
                user_id=user_id,
                query_vector=query_embedding,
                top_k=3,
            )

        # Knowledge retrieval
        knowledge_chunks = []
        if enable_knowledge and self.knowledge_retriever:
            knowledge_chunks = await self.knowledge_retriever.search_knowledge(
                user_id=user_id,
                query=query,
                top_k=self.max_context_chunks,
            )

        # Build system prompt
        system_prompt = self._build_system_prompt(long_term_memories, knowledge_chunks)

        return RAGContext(
            user_id=user_id,
            query=query,
            query_embedding=query_embedding,
            short_term_memory=short_term_memory,
            long_term_memories=long_term_memories,
            knowledge_chunks=knowledge_chunks,
            system_prompt=system_prompt,
        )

    def _build_system_prompt(
        self,
        long_term_memories: List[str],
        knowledge_chunks: List[Dict[str, Any]],
    ) -> str:
        """Build system prompt with retrieved context."""
        base_prompt = "You are a helpful AI assistant for Lumenly."

        # Add long-term memories
        if long_term_memories:
            memories_text = "\n".join([f"- {mem}" for mem in long_term_memories])
            base_prompt += f"\n\nRelevant memories about this user:\n{memories_text}"

        # Add knowledge context
        if knowledge_chunks:
            knowledge_text = "\n\n".join(
                [
                    f"- {chunk.get('chunk_text', chunk.get('text', ''))}"
                    for chunk in knowledge_chunks[: self.max_context_chunks]
                ]
            )
            base_prompt += f"\n\nRelevant knowledge:\n{knowledge_text}"

        return base_prompt

    def _build_messages(
        self,
        query: str,
        context: RAGContext,
    ) -> List[LLMMessage]:
        """Build message list for LLM generation."""
        messages = [LLMMessage(role="system", content=context.system_prompt)]

        # Add conversation history (last 10 turns)
        for msg in context.short_term_memory[-10:]:
            messages.append(
                LLMMessage(role=msg.get("role", "user"), content=msg.get("content", ""))
            )

        # Add current query
        messages.append(LLMMessage(role="user", content=query))

        return messages

    def _validate_response(self, content: str) -> str:
        """Validate and filter LLM response."""
        # Filter output for security
        filtered_content = self.security_validator.filter_output(content)

        # Additional validation could be added here
        # - Length checks
        # - Content safety checks
        # - PII detection

        return filtered_content

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all RAG components."""
        health = {
            "llm_provider": await self.llm_provider.health_check(),
            "embedding_provider": await self.embedding_provider.health_check(),
            "memory_manager": True,  # Memory manager doesn't have health check
        }

        if self.knowledge_retriever:
            health["knowledge_retriever"] = True  # Knowledge retriever doesn't have health check

        return health
