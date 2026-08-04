# apps/backend/app/schemas/document.py
from pydantic import BaseModel, Field


class DocumentInsertRequest(BaseModel):
    document_title: str = Field(..., min_length=1)
    chunk_text: str = Field(..., min_length=1)
    collection_name: str = Field(default="user_documents", min_length=1)


class DocumentInsertResponse(BaseModel):
    status: str
    point_id: str
    collection_name: str


class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    collection_name: str = Field(default="my_knowledge_base", min_length=1)
    limit: int = Field(default=5, ge=1, le=100)


class SearchResultItem(BaseModel):
    id: str
    score: float
    text: str


class DocumentSearchResponse(BaseModel):
    results: list[SearchResultItem]
