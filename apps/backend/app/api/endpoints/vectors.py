# apps/backend/app/api/endpoints/vectors.py
import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastembed import TextEmbedding
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.api.deps import get_current_user
from app.core.qdrant import get_qdrant_client
from app.models.user import User
from app.schemas.document import (
    DocumentInsertRequest,
    DocumentInsertResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    SearchResultItem,
)

router = APIRouter()

VECTOR_SIZE = 384

# Initialize the embedding model (generates 384-dimensional vectors)
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")


async def generate_embedding(text: str) -> list[float]:
    def _embed() -> list[float]:
        return list(embedding_model.embed([text]))[0].tolist()

    return await asyncio.to_thread(_embed)


async def ensure_collection_exists(collection_name: str) -> None:
    client = get_qdrant_client()
    if not await client.collection_exists(collection_name):
        await client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


@router.post(
    "/insert",
    response_model=DocumentInsertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Insert a text document into a Qdrant vector collection",
)
async def insert_document(
    request: DocumentInsertRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentInsertResponse:
    try:
        client = get_qdrant_client()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector database is currently unavailable",
        ) from exc

    try:
        await ensure_collection_exists(request.collection_name)

        point_id = str(uuid.uuid4())
        embedding = await generate_embedding(request.text)

        await client.upsert(
            collection_name=request.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": request.text,
                        "user_id": str(current_user.id),
                    },
                )
            ],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to insert document into vector database",
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

        query_vector = await generate_embedding(request.query)

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
                text=(point.payload or {}).get("text", ""),
            )
            for point in search_response.points
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search documents in vector database",
        ) from exc

    return DocumentSearchResponse(results=results)
