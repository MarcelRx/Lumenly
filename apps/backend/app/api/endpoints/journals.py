# apps/backend/app/api/endpoints/journals.py
import uuid
from datetime import datetime
from typing import Annotated, Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_current_active_user
from app.models.domain import JournalEntry
from app.models.user import User

router = APIRouter()


class JournalEntryCreate(BaseModel):
    """Schema for creating a journal entry."""

    content: str = Field(..., min_length=1, description="Journal entry content")
    mood_score: Optional[int] = Field(None, ge=1, le=10, description="Mood score from 1-10")


class JournalEntryResponse(BaseModel):
    """Schema for journal entry response."""

    id: PydanticObjectId
    user_id: uuid.UUID
    content: str
    mood_score: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "/",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a journal entry",
)
async def create_journal_entry(
    journal_in: JournalEntryCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> JournalEntryResponse:
    """
    Create a new journal entry for the authenticated user.
    The entry is automatically associated with the user's ID.
    """
    journal_entry = JournalEntry(
        user_id=current_user.id,
        content=journal_in.content,
        mood_score=journal_in.mood_score,
    )
    await journal_entry.save()
    return JournalEntryResponse.model_validate(journal_entry)


@router.get(
    "/",
    response_model=list[JournalEntryResponse],
    summary="List journal entries",
)
async def list_journal_entries(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> list[JournalEntryResponse]:
    """
    List all journal entries belonging to the authenticated user.
    This endpoint enforces strict multi-tenant data isolation.
    """
    entries = await JournalEntry.find(JournalEntry.user_id == current_user.id).to_list()
    return [JournalEntryResponse.model_validate(entry) for entry in entries]


@router.get(
    "/{entry_id}",
    response_model=JournalEntryResponse,
    summary="Get a specific journal entry",
)
async def get_journal_entry(
    entry_id: PydanticObjectId,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> JournalEntryResponse:
    """
    Get a specific journal entry by ID.
    Returns 404 if the entry doesn't exist or doesn't belong to the user.
    """
    entry = await JournalEntry.get(entry_id)

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found",
        )

    # Enforce multi-tenant isolation
    if entry.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found",
        )

    return JournalEntryResponse.model_validate(entry)
