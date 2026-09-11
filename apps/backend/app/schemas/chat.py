# apps/backend/app/schemas/chat.py
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="User's query")
    collection_name: str = Field(
        default="test_collection", description="Collection name for vector search"
    )


class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI-generated answer")
    context: list = Field(default_factory=list, description="Context used to generate the answer")
