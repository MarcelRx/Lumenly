# apps/backend/app/api/endpoints/chat.py
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import generate_rag_response

router = APIRouter()


@router.post("/ask", response_model=ChatResponse)
async def ask(
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatResponse:
    """
    Generate a RAG response for the user's query.

    This endpoint:
    - Requires authentication via JWT token
    - Retrieves relevant context from Qdrant filtered by user_id
    - Generates an answer using Gemini 2.5 Flash Preview API
    - Returns the answer along with retrieved context chunks
    """
    # Rate limiting is enforced inside generate_rag_response, but we also log if limit is hit
    response = await generate_rag_response(
        query=request.query,
        user_id=str(current_user.id),
        collection_name=request.collection_name,
    )
    return response
