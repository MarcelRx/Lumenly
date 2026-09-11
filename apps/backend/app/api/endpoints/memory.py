# apps/backend/app/api/endpoints/memory.py
"""
Memory API Endpoints - REST API for Memory Intelligence Core.

This module provides REST endpoints for memory operations:
- Create, list, retrieve, delete memories
- Archive and summarize memories
- Search memories with filtering
- Memory statistics and behavior summary
All endpoints require authentication and enforce multi-tenant isolation.
"""
from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.ai.memory import (
    MemoryImportance,
    MemoryRecord,
    MemoryRetrievalConfig,
    MemoryType,
)
from app.ai.memory.manager import MemoryManager
from app.ai.memory.validation import MemoryValidationError, default_validator
from app.api.deps import get_current_active_user
from app.models.user import User

router = APIRouter()


# Request/Response Schemas
class MemoryCreateRequest(BaseModel):
    """Request schema for creating a memory."""
    memory_type: MemoryType = Field(..., description="Type of memory to create")
    content: str = Field(..., min_length=1, max_length=100_000, description="Memory content")
    importance: MemoryImportance = Field(
        default=MemoryImportance.MEDIUM,
        description="Importance level of the memory"
    )
    source: Optional[str] = Field(
        default="user_input",
        max_length=500,
        description="Source of the memory"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for the memory"
    )

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate tags list length and individual tag length."""
        if len(v) > 100:
            raise ValueError("Maximum 100 tags allowed")
        for tag in v:
            if len(tag) > 100:
                raise ValueError("Each tag must be at most 100 characters")
        return v


class MemoryResponse(BaseModel):
    """Response schema for a memory."""
    id: str
    user_id: str
    memory_type: str
    content: str
    importance: str
    source: Optional[str]
    tags: List[str]
    created_at: datetime
    updated_at: Optional[datetime]
    access_count: int
    last_accessed: Optional[datetime]

    @classmethod
    def from_record(cls, record: MemoryRecord) -> "MemoryResponse":
        return cls(
            id=record.id,
            user_id=record.user_id,
            memory_type=record.memory_type.value,
            content=record.content,
            importance=record.metadata.importance.value,
            source=record.metadata.source,
            tags=record.metadata.tags,
            created_at=record.created_at,
            updated_at=record.metadata.updated_at,
            access_count=record.metadata.access_count,
            last_accessed=record.metadata.last_accessed,
        )


class MemorySearchRequest(BaseModel):
    """Request schema for memory search."""
    query: str = Field(..., min_length=1, max_length=10_000, description="Search query")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results to return")
    memory_types: Optional[List[str]] = Field(
        default=None,
        description="Filter by memory types"
    )
    enable_ranking: bool = Field(default=True, description="Enable result ranking")
    enable_semantic_search: bool = Field(default=True, description="Enable semantic search")


class MemorySearchResponse(BaseModel):
    """Response schema for memory search results."""
    results: List[dict]
    total_count: int
    query: str


class MemoryUpdateRequest(BaseModel):
    """Request schema for updating a memory."""
    content: Optional[str] = Field(None, description="Updated memory content")
    importance: Optional[MemoryImportance] = Field(None, description="Updated importance level")
    tags: Optional[List[str]] = Field(None, description="Updated tags")


class MemoryStatisticsResponse(BaseModel):
    """Response schema for memory statistics."""
    total_memories: int
    counts_by_type: dict
    recent_memory_count: int
    last_activity: Optional[datetime]
    generated_at: datetime


class BehaviorSummaryResponse(BaseModel):
    """Response schema for behavior summary."""
    total_behavioral_events: int
    conversation_frequency: dict
    goal_completion_rate: dict
    habit_streak_summary: dict
    journal_statistics: dict
    overall_engagement: dict
    generated_at: datetime


class MemoryConsolidationResponse(BaseModel):
    """Response schema for memory consolidation."""
    consolidated_count: int
    source_memory_ids: List[str]
    message: str


class MemoryCleanupResponse(BaseModel):
    """Response schema for memory cleanup."""
    kept: int
    archived: int
    compressed: int
    summarized: int
    deleted: int
    total_evaluated: int
    message: str


# Dependency to get Memory Manager
async def get_memory_manager() -> MemoryManager:
    """Dependency to get the Memory Manager instance."""
    # In production, this would be initialized with proper dependencies
    return MemoryManager()


@router.post(
    "/",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new memory",
)
async def create_memory(
    current_user: Annotated[User, Depends(get_current_active_user)],
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
    request: MemoryCreateRequest,
) -> MemoryResponse:
    """
    Create a new memory for the current user.

    - **memory_type**: Type of memory (conversation, journal, goal, etc.)
    - **content**: Memory content
    - **importance**: Importance level (critical, high, medium, low, temporary)
    - **source**: Source of the memory (default: user_input)
    - **tags**: Optional tags for categorization
    """
    try:
        # Validate payload size
        import json
        payload_size = len(json.dumps(request.model_dump()).encode('utf-8'))
        default_validator.validate_payload_size(payload_size)

        from app.ai.memory.schema import MemoryMetadata

        metadata = MemoryMetadata(
            user_id=str(current_user.id),
            memory_type=request.memory_type,
            importance=request.importance,
            source=request.source,
            tags=request.tags,
        )

        memory_id = await memory_manager.store_memory(
            user_id=str(current_user.id),
            memory_type=request.memory_type,
            content=request.content,
            metadata=metadata,
        )

        memory = await memory_manager.get_memory_by_id(memory_id, str(current_user.id))
        if not memory:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created memory"
            )

        return MemoryResponse.from_record(memory)

    except MemoryValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Memory validation failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create memory: {str(e)}"
        )


@router.get(
    "/",
    response_model=List[MemoryResponse],
    summary="List all memories for current user",
)
async def list_memories(
    current_user: Annotated[User, Depends(get_current_active_user)],
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
    memory_type: Optional[MemoryType] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[MemoryResponse]:
    """
    List memories for the current user with optional filtering.

    - **memory_type**: Optional filter by memory type
    - **limit**: Maximum number of results (default: 100)
    - **offset**: Offset for pagination (default: 0)
    """
    try:
        memories = await memory_manager.list_memories(
            user_id=str(current_user.id),
            memory_type=memory_type,
            limit=limit,
            offset=offset,
        )

        return [MemoryResponse.from_record(mem) for mem in memories]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list memories: {str(e)}"
        )


@router.get(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Retrieve a specific memory by ID",
)
async def get_memory(
    current_user: Annotated[User, Depends(get_current_active_user)],
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
    memory_id: str,
) -> MemoryResponse:
    """
    Retrieve a specific memory by ID.

    Enforces multi-tenant isolation - users can only access their own memories.
    """
    try:
        memory = await memory_manager.get_memory_by_id(memory_id, str(current_user.id))

        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )

        return MemoryResponse.from_record(memory)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memory: {str(e)}"
        )


@router.put(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Update a specific memory",
)
async def update_memory(
    current_user: Annotated[User, Depends(get_current_active_user)],
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
    memory_id: str,
    request: MemoryUpdateRequest,
) -> MemoryResponse:
    """
    Update a specific memory.

    - **content**: Updated memory content (optional)
    - **importance**: Updated importance level (optional)
    - **tags**: Updated tags (optional)
    """
    try:
        # Verify memory exists and belongs to user
        existing = await memory_manager.get_memory_by_id(memory_id, str(current_user.id))
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )

        # Build updates
        updates = {}
        if request.content is not None:
            updates["content"] = request.content
        if request.importance is not None:
            updates["importance"] = request.importance.value
        if request.tags is not None:
            updates["tags"] = request.tags

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No updates provided"
            )

        success = await memory_manager.update_memory(
            memory_id=memory_id,
            user_id=str(current_user.id),
            updates=updates,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update memory"
            )

        # Return updated memory
        updated = await memory_manager.get_memory_by_id(memory_id, str(current_user.id))
        return MemoryResponse.from_record(updated)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update memory: {str(e)}"
        )


@router.delete(
    "/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a specific memory",
)
async def delete_memory(
    current_user: Annotated[User, Depends(get_current_active_user)],
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
    memory_id: str,
) -> None:
    """
    Delete a specific memory.

    Enforces multi-tenant isolation - users can only delete their own memories.
    """
    try:
        # Verify memory exists and belongs to user
        existing = await memory_manager.get_memory_by_id(memory_id, str(current_user.id))
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )

        success = await memory_manager.delete_memory(
            memory_id=memory_id,
            user_id=str(current_user.id),
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete memory"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete memory: {str(e)}"
        )


@router.post(
    "/search",
    response_model=MemorySearchResponse,
    summary="Search memories with ranking",
)
async def search_memories(
    current_user: Annotated[User, Depends(get_current_active_user)],
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
    request: MemorySearchRequest,
) -> MemorySearchResponse:
    """
    Search memories with ranking and filtering.

    - **query**: Search query string
    - **max_results**: Maximum results to return (default: 10)
    - **memory_types**: Optional filter by memory types
    - **enable_ranking**: Enable result ranking (default: true)
    - **enable_semantic_search**: Enable semantic search (default: true)
    """
    try:
        config = MemoryRetrievalConfig(
            max_results=request.max_results,
            memory_types=request.memory_types,
            enable_ranking=request.enable_ranking,
            enable_semantic_search=request.enable_semantic_search,
        )

        results = await memory_manager.retrieve_memories(
            user_id=str(current_user.id),
            query=request.query,
            config=config,
        )

        formatted_results = []
        for result in results:
            formatted_results.append({
                "memory": MemoryResponse.from_record(result.memory).model_dump(),
                "score": result.score,
                "rank": result.rank,
                "relevance_factors": result.relevance_factors,
            })

        return MemorySearchResponse(
            results=formatted_results,
            total_count=len(formatted_results),
            query=request.query,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search memories: {str(e)}"
        )


@router.post(
    "/{memory_id}/archive",
    status_code=status.HTTP_200_OK,
    summary="Archive a memory",
)
async def archive_memory(
    current_user: Annotated[User, Depends(get_current_active_user)],
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
    memory_id: str,
) -> dict:
    """
    Archive a memory instead of deleting it.

    Archived memories are preserved but not returned in normal searches.
    """
    try:
        # Verify memory exists and belongs to user
        existing = await memory_manager.get_memory_by_id(memory_id, str(current_user.id))
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )

        success = await memory_manager.storage.archive_memory(memory_id, str(current_user.id))

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to archive memory"
            )

        return {"message": "Memory archived successfully", "memory_id": memory_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive memory: {str(e)}"
        )


@router.post(
    "/{memory_id}/summarize",
    response_model=dict,
    summary="Summarize a memory",
)
async def summarize_memory(
    current_user: Annotated[User, Depends(get_current_active_user)],
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
    memory_id: str,
) -> dict:
    """
    Generate a summary of a specific memory.
    """
    try:
        summary = await memory_manager.summarize_memory(memory_id, str(current_user.id))

        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found or summarization failed"
            )

        return {
            "memory_id": memory_id,
            "summary": summary,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to summarize memory: {str(e)}"
        )


@router.get(
    "/statistics/overview",
    response_model=MemoryStatisticsResponse,
    summary="Get memory statistics",
)
async def get_memory_statistics(
    current_user: Annotated[User, Depends(get_current_active_user)],
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
) -> MemoryStatisticsResponse:
    """
    Get comprehensive statistics about the user's memories.
    """
    try:
        stats = await memory_manager.get_memory_statistics(str(current_user.id))

        return MemoryStatisticsResponse.model_validate(stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory statistics: {str(e)}"
        )


@router.get(
    "/behavior/summary",
    response_model=BehaviorSummaryResponse,
    summary="Get behavior summary",
)
async def get_behavior_summary(
    current_user: Annotated[User, Depends(get_current_active_user)],
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
) -> BehaviorSummaryResponse:
    """
    Get behavioral summary for the user.
    """
    try:
        summary = await memory_manager.get_behavior_summary(str(current_user.id))

        return BehaviorSummaryResponse.model_validate(summary)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get behavior summary: {str(e)}"
        )


@router.post(
    "/consolidate",
    response_model=MemoryConsolidationResponse,
    summary="Consolidate similar memories",
)
async def consolidate_memories(
    current_user: Annotated[User, Depends(get_current_active_user)],
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
    memory_type: Optional[MemoryType] = None,
) -> MemoryConsolidationResponse:
    """
    Consolidate similar memories for the user.

    - **memory_type**: Optional filter by memory type (consolidates all types if not specified)
    """
    try:
        results = await memory_manager.consolidate_user_memories(
            user_id=str(current_user.id),
            memory_type=memory_type,
        )

        source_ids = []
        for result in results:
            source_ids.extend(result.source_memory_ids)

        return MemoryConsolidationResponse(
            consolidated_count=len(results),
            source_memory_ids=source_ids,
            message=f"Consolidated {len(results)} memory groups",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to consolidate memories: {str(e)}"
        )


@router.post(
    "/cleanup",
    response_model=MemoryCleanupResponse,
    summary="Clean up memories using forgetting policy",
)
async def cleanup_memories(
    current_user: Annotated[User, Depends(get_current_active_user)],
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
    policy_name: str = "default",
) -> MemoryCleanupResponse:
    """
    Clean up memories using the specified forgetting policy.

    - **policy_name**: Name of the forgetting policy to use (default: "default")
    """
    try:
        results = await memory_manager.cleanup_user_memories(
            user_id=str(current_user.id),
            policy_name=policy_name,
        )

        return MemoryCleanupResponse.model_validate({
            **results,
            "message": f"Memory cleanup completed using policy '{policy_name}'",
        })

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup memories: {str(e)}"
        )
