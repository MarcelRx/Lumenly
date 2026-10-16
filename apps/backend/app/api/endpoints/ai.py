# apps/backend/app/api/endpoints/ai.py
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.ai.llm import LLMProviderError
from app.ai.rag.orchestrator import RAGOrchestrator
from app.api.deps import get_current_active_user, get_rag_orchestrator
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class AIQueryRequest(BaseModel):
    """Request schema for AI query endpoint."""

    query: str = Field(
        ..., min_length=1, max_length=10000, description="The user's question or query"
    )


class AIQueryResponse(BaseModel):
    """Response schema for AI query endpoint."""

    answer: str = Field(..., description="The AI-generated answer")
    context_used: dict = Field(default_factory=dict, description="Context used for generation")
    retrieval_stats: dict = Field(default_factory=dict, description="Retrieval statistics")


@router.post("/ask", response_model=AIQueryResponse)
async def ask_ai(
    ai_request: AIQueryRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    rag_orchestrator: Annotated[RAGOrchestrator, Depends(get_rag_orchestrator)],
) -> AIQueryResponse:
    """
    Ask a question using RAG (Retrieval-Augmented Generation).

    This endpoint uses the canonical RAGOrchestrator which:
    1. Validates the request for security (prompt injection, input sanitization)
    2. Generates an embedding for the user's query using the configured provider
    3. Retrieves relevant context from memory and knowledge base
    4. Generates an AI response using the configured LLM provider
    5. Validates and filters the response
    6. Persists the conversation turn to memory

    Requires authentication. Multi-tenant isolation is enforced by user_id.
    """
    try:
        # Process the query through the RAG orchestrator
        rag_response = await rag_orchestrator.process_query(
            user_id=str(current_user.id),
            query=ai_request.query,
            enable_memory=True,
            enable_knowledge=True,
        )

        logger.info(
            f"AI query processed for user {current_user.id}, "
            f"context_items={rag_response.retrieval_stats.get('total_context_items', 0)}, "
            f"security_validated={rag_response.security_validation}"
        )

        return AIQueryResponse(
            answer=rag_response.content,
            context_used=rag_response.context_used,
            retrieval_stats=rag_response.retrieval_stats,
        )

    except LLMProviderError as e:
        logger.error(f"LLM provider error for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable. Please try again later.",
        )
    except ValueError as e:
        logger.error(f"Validation error for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request. Please check your input.",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error processing AI query for user {current_user.id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
        )
