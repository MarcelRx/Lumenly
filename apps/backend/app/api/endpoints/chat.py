# apps/backend/app/api/endpoints/chat.py
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.llm import LLMProviderError
from app.ai.rag.orchestrator import RAGOrchestrator
from app.api.deps import get_current_user, get_rag_orchestrator
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ask", response_model=ChatResponse)
async def ask(
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    rag_orchestrator: Annotated[RAGOrchestrator, Depends(get_rag_orchestrator)],
) -> ChatResponse:
    """
    Generate a RAG response for the user's query.

    This endpoint uses the canonical RAGOrchestrator which:
    - Requires authentication via JWT token
    - Validates the request for security (prompt injection, input sanitization)
    - Retrieves relevant context from memory and knowledge base filtered by user_id
    - Generates an answer using the configured LLM provider
    - Validates and filters the response
    - Persists the conversation turn to memory
    - Returns the answer along with retrieved context chunks

    Multi-tenant isolation is enforced by user_id at all data access points.
    """
    try:
        # Process the query through the RAG orchestrator
        rag_response = await rag_orchestrator.process_query(
            user_id=str(current_user.id),
            query=request.query,
            enable_memory=True,
            enable_knowledge=True,
        )

        # Build context list for backward compatibility with existing ChatResponse schema
        context_list = []
        if rag_response.context_used.get("short_term_messages", 0) > 0:
            context_list.append(f"Short-term memory: {rag_response.context_used['short_term_messages']} messages")
        if rag_response.context_used.get("long_term_memories", 0) > 0:
            context_list.append(f"Long-term memories: {rag_response.context_used['long_term_memories']} memories")
        if rag_response.context_used.get("knowledge_chunks", 0) > 0:
            context_list.append(f"Knowledge chunks: {rag_response.context_used['knowledge_chunks']} chunks")

        return ChatResponse(
            answer=rag_response.content,
            context=context_list,
        )

    except LLMProviderError as e:
        logger.error(f"LLM provider error for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable. Please try again later."
        )
    except ValueError as e:
        logger.error(f"Validation error for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request. Please check your input."
        )
    except Exception as e:
        logger.error(f"Unexpected error processing chat query for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )
