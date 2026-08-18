# apps/backend/app/api/endpoints/documents.py
import uuid
from datetime import datetime
from typing import Annotated, Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_current_active_user
from app.models.domain import DocumentStatus, UserDocument
from app.models.user import User
from app.workers.tasks import process_document_task

router = APIRouter()


class DocumentUploadRequest(BaseModel):
    """Schema for document upload request."""
    filename: str = Field(..., min_length=1, description="Original filename")
    content: str = Field(..., min_length=1, description="Document text content")


class DocumentResponse(BaseModel):
    """Schema for document response."""
    id: PydanticObjectId
    user_id: uuid.UUID
    filename: str
    content: str
    vector_ids: list[str]
    status: DocumentStatus
    chunk_count: int
    error_message: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "/",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a document for processing",
)
async def upload_document(
    document_in: DocumentUploadRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> DocumentResponse:
    """
    Upload a new document for asynchronous processing.

    The document is saved in PENDING status and a Celery task is triggered
    to process it (chunk text, generate embeddings, store in Qdrant).

    Returns 202 Accepted to indicate asynchronous processing has begun.
    """
    document = UserDocument(
        user_id=current_user.id,
        filename=document_in.filename,
        content=document_in.content,
        status=DocumentStatus.PENDING,
    )
    await document.save()

    # Trigger asynchronous processing with explicit user context for multi-tenant isolation
    process_document_task.delay(str(document.id), str(current_user.id))

    return DocumentResponse.model_validate(document)


@router.get(
    "/",
    response_model=list[DocumentResponse],
    summary="List documents",
)
async def list_documents(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> list[DocumentResponse]:
    """
    List all documents belonging to the authenticated user.
    This endpoint enforces strict multi-tenant data isolation.
    """
    documents = await UserDocument.find(UserDocument.user_id == current_user.id).to_list()
    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get a specific document",
)
async def get_document(
    document_id: PydanticObjectId,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> DocumentResponse:
    """
    Get a specific document by ID including its processing status.

    Returns 404 if the document doesn't exist or doesn't belong to the user.
    """
    document = await UserDocument.get(document_id)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Enforce multi-tenant isolation
    if document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return DocumentResponse.model_validate(document)
