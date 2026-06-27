# apps/backend/app/schemas/chat.py
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="User's query/question")
    collection_name: str = Field(
        default="documents",
        min_length=1,
        max_length=200,
        description="Qdrant collection to retrieve context from",
    )


class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI-generated response")
    context: list[str] = Field(default_factory=list, description="Retrieved context chunks")
