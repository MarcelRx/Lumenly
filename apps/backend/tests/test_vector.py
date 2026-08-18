# apps/backend/tests/test_vector.py
import random
import uuid

import pytest

from app.services.vector import vector_service


@pytest.mark.asyncio
async def test_ensure_collection(cleanup_qdrant) -> None:
    """Test that the Qdrant collection is created successfully."""
    await vector_service.ensure_collection()

    # Verify collection exists by trying to get it
    client = await vector_service._get_client()
    collections = await client.get_collections()
    collection_names = [c.name for c in collections.collections]

    assert "lumenly_vectors" in collection_names


@pytest.mark.asyncio
async def test_upsert_vector(cleanup_qdrant) -> None:
    """Test upserting a vector to Qdrant."""
    await vector_service.ensure_collection()

    # Generate a mock 1536-dimensional embedding
    vector_id = str(uuid.uuid4())
    embedding = [random.random() for _ in range(1536)]

    payload = {
        "user_id": str(uuid.uuid4()),
        "document_id": str(uuid.uuid4()),
        "filename": "test.txt",
    }

    await vector_service.upsert_vector(vector_id, embedding, payload)

    # Verify the vector was upserted by searching for it
    results = await vector_service.search_vectors(
        user_id=payload["user_id"],
        query_embedding=embedding,
        limit=1,
    )

    assert len(results) > 0
    assert results[0].id == vector_id


@pytest.mark.asyncio
async def test_search_vectors(cleanup_qdrant) -> None:
    """Test searching vectors with user_id filtering."""
    await vector_service.ensure_collection()

    user_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())

    # Create multiple vectors for the same user
    for i in range(3):
        vector_id = str(uuid.uuid4())
        embedding = [random.random() for _ in range(1536)]

        payload = {
            "user_id": user_id,
            "document_id": document_id,
            "filename": f"file_{i}.txt",
        }

        await vector_service.upsert_vector(vector_id, embedding, payload)

    # Search for vectors
    query_embedding = [random.random() for _ in range(1536)]
    results = await vector_service.search_vectors(
        user_id=user_id,
        query_embedding=query_embedding,
        limit=5,
    )

    # Should find at least the 3 vectors we upserted
    assert len(results) >= 3

    # All results should belong to the same user
    for result in results:
        assert result.payload["user_id"] == user_id


@pytest.mark.asyncio
async def test_search_vectors_user_isolation(cleanup_qdrant) -> None:
    """Test that search is strictly filtered by user_id (multi-tenant isolation)."""
    await vector_service.ensure_collection()

    user_id_1 = str(uuid.uuid4())
    user_id_2 = str(uuid.uuid4())

    # Create vectors for user 1
    for i in range(2):
        vector_id = str(uuid.uuid4())
        embedding = [random.random() for _ in range(1536)]

        payload = {
            "user_id": user_id_1,
            "document_id": str(uuid.uuid4()),
            "filename": f"user1_file_{i}.txt",
        }

        await vector_service.upsert_vector(vector_id, embedding, payload)

    # Create vectors for user 2
    for i in range(2):
        vector_id = str(uuid.uuid4())
        embedding = [random.random() for _ in range(1536)]

        payload = {
            "user_id": user_id_2,
            "document_id": str(uuid.uuid4()),
            "filename": f"user2_file_{i}.txt",
        }

        await vector_service.upsert_vector(vector_id, embedding, payload)

    # Search as user 1
    query_embedding = [random.random() for _ in range(1536)]
    results_1 = await vector_service.search_vectors(
        user_id=user_id_1,
        query_embedding=query_embedding,
        limit=10,
    )

    # All results should belong to user 1
    for result in results_1:
        assert result.payload["user_id"] == user_id_1
        assert result.payload["user_id"] != user_id_2

    # Search as user 2
    results_2 = await vector_service.search_vectors(
        user_id=user_id_2,
        query_embedding=query_embedding,
        limit=10,
    )

    # All results should belong to user 2
    for result in results_2:
        assert result.payload["user_id"] == user_id_2
        assert result.payload["user_id"] != user_id_1


@pytest.mark.asyncio
async def test_upsert_vector_missing_required_fields(cleanup_qdrant) -> None:
    """Test that upserting a vector without required payload fields raises an error."""
    await vector_service.ensure_collection()

    vector_id = str(uuid.uuid4())
    embedding = [random.random() for _ in range(1536)]

    # Missing user_id
    payload_missing_user = {
        "document_id": str(uuid.uuid4()),
        "filename": "test.txt",
    }

    with pytest.raises(ValueError, match="must include 'user_id' and 'document_id'"):
        await vector_service.upsert_vector(vector_id, embedding, payload_missing_user)

    # Missing document_id
    payload_missing_doc = {
        "user_id": str(uuid.uuid4()),
        "filename": "test.txt",
    }

    with pytest.raises(ValueError, match="must include 'user_id' and 'document_id'"):
        await vector_service.upsert_vector(vector_id, embedding, payload_missing_doc)


@pytest.mark.asyncio
async def test_upsert_vector_update_existing(cleanup_qdrant) -> None:
    """Test that upserting updates an existing vector with the same ID."""
    await vector_service.ensure_collection()

    user_id = str(uuid.uuid4())
    vector_id = str(uuid.uuid4())

    # Initial upsert
    embedding_1 = [random.random() for _ in range(1536)]
    payload_1 = {
        "user_id": user_id,
        "document_id": str(uuid.uuid4()),
        "filename": "original.txt",
    }

    await vector_service.upsert_vector(vector_id, embedding_1, payload_1)

    # Update with new payload
    embedding_2 = [random.random() for _ in range(1536)]
    payload_2 = {
        "user_id": user_id,
        "document_id": str(uuid.uuid4()),
        "filename": "updated.txt",
    }

    await vector_service.upsert_vector(vector_id, embedding_2, payload_2)

    # Verify the update
    results = await vector_service.search_vectors(
        user_id=user_id,
        query_embedding=embedding_2,
        limit=1,
    )

    assert len(results) > 0
    assert results[0].id == vector_id
    assert results[0].payload["filename"] == "updated.txt"
