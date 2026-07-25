# apps/backend/app/schemas/chat.py
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    message: str = Field(..., min_length=1, max_length=2000, description="User's message")


class ChatResponse(BaseModel):
    response: str = Field(..., description="AI-generated response")
    agent_used: str = Field(..., description="The agent/coach that handled the query")
    memories_retrieved: int = Field(..., description="Number of memories retrieved from long-term storage")
    knowledge_snippets_used: int = Field(..., description="Number of knowledge snippets used")
