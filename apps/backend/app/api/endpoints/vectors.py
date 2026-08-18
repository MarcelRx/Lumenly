# apps/backend/app/api/endpoints/vectors.py
import logging
import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.api.deps import get_current_user, get_embedding_provider
from app.core.config import settings
from app.db.qdrant import get_qdrant_client
from app.models.user import User
from app.schemas.document import (
    DocumentInsertRequest,
    DocumentInsertResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    SearchResultItem,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Define the standardized collection name for Dashboard management
COLLECTION_NAME = "knowledge_base"

# VECTOR_DIMENSION is the single source of truth for vector dimensions
# All embedding providers must be configured to match this dimension
VECTOR_SIZE = settings.VECTOR_DIMENSION


# -------------------------------------------------------------
# STEP 3: DASHBOARD SCHEMAS
# -------------------------------------------------------------

class KnowledgeBaseDocument(BaseModel):
    """Represents a single unique document found in the knowledge base."""
    # We use a combined key "userid::title" for unique ID for now
    id: str = Field(..., description="Unique ID for this document (UserID::Title).")
    title: str = Field(..., description="The title of the document.")
    chunk_count: int = Field(..., description="Number of vectors/chunks belonging to this document.")


class DocumentListResponse(BaseModel):
    """Response containing the aggregated list of unique documents."""
    status: str = Field("success")
    documents: List[KnowledgeBaseDocument] = Field(default_factory=list)


# -------------------------------------------------------------
# INTERNAL HELPERS
# -------------------------------------------------------------

async def generate_embedding(text: str, embedding_provider) -> list[float]:
    """Generate embedding using the configured embedding provider."""
    # Use the injected embedding provider from the canonical architecture
    return await embedding_provider.embed(text)


async def ensure_collection_exists(collection_name: str) -> None:
    client = get_qdrant_client()
    if not await client.collection_exists(collection_name):
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=getattr(Distance, settings.DISTANCE_METRIC.upper(), Distance.COSINE)
            ),
        )

# -------------------------------------------------------------
# STEP 3, TASK B: DASHBOARD GET API ENDPOINT
# -------------------------------------------------------------

@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List unique document titles and stats in the knowledge base",
    tags=["Dashboard"]
)
async def list_knowledge_base_documents(
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentListResponse:
    """
    Retrieves aggregated document info from Qdrant filtered by user_id.

    Requires authentication via JWT token.
    Uses 'knowledge_base' collection.
    Scans point payloads to group by document_title and count chunks.
    """
    try:
        client = get_qdrant_client()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector database is currently unavailable",
        ) from exc

    try:
        if not await client.collection_exists(COLLECTION_NAME):
            return DocumentListResponse(documents=[])

        user_id_str = str(current_user.id)

        # Retrieve all payloads belonging to the current user
        points, _ = await client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id_str),
                    )
                ]
            ),
            with_payload=True,
            with_vectors=False,
            limit=5000,
        )

        # Group by document title
        unique_docs_map: dict[str, dict] = {}

        for point in points:
            payload = point.payload or {}

            doc_title = payload.get("document_title")
            payload_user_id = payload.get("user_id")

            if not doc_title or payload_user_id != user_id_str:
                continue

            doc_key = f"{user_id_str}::{doc_title}"

            if doc_key not in unique_docs_map:
                unique_docs_map[doc_key] = {
                    "id": doc_key,
                    "title": doc_title,
                    "chunk_count": 0,
                }

            unique_docs_map[doc_key]["chunk_count"] += 1

        documents = [
            KnowledgeBaseDocument(**doc)
            for doc in unique_docs_map.values()
        ]

        logger.info(
            "Retrieved %d documents for user %s",
            len(documents),
            user_id_str,
        )

        return DocumentListResponse(
            status="success",
            documents=documents,
        )

    except Exception as exc:
        logger.error(f"Failed to list knowledge base documents: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve knowledge base list: {str(exc)}",
        ) from exc


# -------------------------------------------------------------
# STEP 3, TASK D: Backend Delete service (Integrated)
# -------------------------------------------------------------

# We use the unique dashboard ID (UserID::Title) in the URL path
@router.delete(
    "/documents/{doc_key}",
    status_code=status.HTTP_200_OK,
    summary="Delete all vectors chunks belonging to a single unique document title.",
    tags=["Dashboard"]
)
async def delete_knowledge_base_document(
    doc_key: str, # Combined key defined in GET logic above (UserId::Title)
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Deletes every vector chunk associated with a document title, filtered by the current user.
    Uses UserId::Title as unique identifier for orchestration.

    Requires authentication via JWT token.
    Uses UserId comparison on key for authorization.
    """
    try:
        client = get_qdrant_client()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector database is currently unavailable",
        ) from exc

    try:
        if not await client.collection_exists(COLLECTION_NAME):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base is empty.")

        # 1. Authorize the user (Key parsing logic)
        # We split the key f"{userid}::{title}" safely
        current_user_id_str = str(current_user.id)

        # Split at first occurrence of '::'
        key_parts = doc_key.split("::", 1)

        if len(key_parts) != 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Document Key provided.")

        payload_user_id = key_parts[0]
        payload_doc_title = key_parts[1]

        # Authorization check: UserId comparison must match
        if payload_user_id != current_user_id_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to delete this document."
            )

        logger.info(f"Authorized deletion request: Document '{payload_doc_title}' for user {current_user_id_str}")

        # 2. Perform the destruction filter in Qdrant (Destroy point by filtering)
        points_filter = Filter(
            must=[
                # User_id must match...
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=current_user_id_str),
                ),
                # ...AND document_title must match the specific title
                FieldCondition(
                    key="document_title",
                    match=MatchValue(value=payload_doc_title),
                )
            ]
        )

        logger.debug(f"Executing Qdrant deletion filter on {COLLECTION_NAME} for {payload_doc_title}")

        # Call Qdrant delete with filter (magic)
        await client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=points_filter,
        )

        logger.info(f"SUCCESS: Deleted document '{payload_doc_title}' vector chunks from {COLLECTION_NAME}.")

        return {
            "status": "success",
            "message": f"Successfully deleted vectors for document '{payload_doc_title}'."
        }

    except HTTPException as hexc:
        # Re-raise explicit HTTP exceptions
        raise hexc
    except Exception as exc:
        logger.error(f"Deletion service failure: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deletes from vector database failed: {str(exc)}",
        ) from exc


# -------------------------------------------------------------
# EXISTING AGENT ROUTING / INSERT ENDPOINTS
# -------------------------------------------------------------

@router.post(
    "/insert",
    response_model=DocumentInsertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Insert a text document into a Qdrant vector collection",
)
async def insert_document(
    request: DocumentInsertRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    embedding_provider = Depends(get_embedding_provider),
) -> DocumentInsertResponse:
    try:
        client = get_qdrant_client()
    except RuntimeError as exc:
        logger.error(f"Vector DB unavailable: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector database is currently unavailable",
        ) from exc

    try:
        await ensure_collection_exists(request.collection_name)

        point_id = str(uuid.uuid4())

        # Generate embedding from the chunk_text using the canonical provider
        embedding = await generate_embedding(request.chunk_text, embedding_provider)

        # Validate embedding dimension matches configured dimension
        if len(embedding) != VECTOR_SIZE:
            raise ValueError(
                f"Embedding dimension mismatch: expected {VECTOR_SIZE}, got {len(embedding)}. "
                f"Provider configuration must match VECTOR_DIMENSION setting."
            )

        # Save payload using the keys expected by KnowledgeRetriever
        await client.upsert(
            collection_name=request.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "document_title": request.document_title,
                        "chunk_text": request.chunk_text,
                        "user_id": str(current_user.id),
                    },
                )
            ],
        )
    except Exception as exc:
        logger.error(f"Failed to insert document into vector database: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to insert document into vector database: {str(exc)}",
        ) from exc

    return DocumentInsertResponse(
        status="success",
        point_id=point_id,
        collection_name=request.collection_name,
    )


@router.post(
    "/search",
    response_model=DocumentSearchResponse,
    summary="Semantically search documents in a Qdrant vector collection",
)
async def search_documents(
    request: DocumentSearchRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    embedding_provider = Depends(get_embedding_provider),
) -> DocumentSearchResponse:
    try:
        client = get_qdrant_client()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector database is currently unavailable",
        ) from exc

    try:
        if not await client.collection_exists(request.collection_name):
            return DocumentSearchResponse(results=[])

        query_vector = await generate_embedding(request.query, embedding_provider)

        # Validate embedding dimension matches configured dimension
        if len(query_vector) != VECTOR_SIZE:
            raise ValueError(
                f"Embedding dimension mismatch: expected {VECTOR_SIZE}, got {len(query_vector)}. "
                f"Provider configuration must match VECTOR_DIMENSION setting."
            )

        search_response = await client.query_points(
            collection_name=request.collection_name,
            query=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=str(current_user.id)),
                    )
                ]
            ),
            limit=request.limit,
            with_payload=True,
        )

        results = [
            SearchResultItem(
                id=str(point.id),
                score=point.score,
                text=(point.payload or {}).get("chunk_text", ""),
            )
            for point in search_response.points
        ]
    except Exception as exc:
        logger.error(f"Failed to search documents in vector database: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search documents in vector database: {str(exc)}",
        ) from exc

    return DocumentSearchResponse(results=results)
