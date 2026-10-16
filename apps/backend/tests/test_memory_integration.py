# apps/backend/tests/test_memory_integration.py
"""
Integration tests for Memory Intelligence Core.

These tests verify the integration of all memory components:
- End-to-end memory lifecycle
- API endpoint integration
- Database operations
- Security integration
"""
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.memory import router as memory_router


@pytest.fixture
async def test_app():
    """Create a test FastAPI app with memory endpoints."""
    app = FastAPI(title="Test Memory API")
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(memory_router, prefix="/api/v1/memory", tags=["memory"])

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


@pytest.fixture
async def client(test_app):
    """Create an async test client."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestMemoryAPIIntegration:
    """Test memory API endpoint integration."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Test health endpoint is accessible."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_memory_endpoints_exist(self, client):
        """Test that memory endpoints are registered."""
        # Test that endpoints return 401 when not authenticated
        response = await client.get("/api/v1/memory/")
        assert response.status_code == 401  # Unauthorized

        response = await client.post("/api/v1/memory/search", json={"query": "test"})
        assert response.status_code == 401  # Unauthorized


class TestMemoryDatabaseIntegration:
    """Test memory database integration."""

    @pytest.mark.asyncio
    async def test_memory_storage_integration(self, setup_databases):
        """Test memory storage with real databases."""
        from app.ai.memory import MemoryImportance, MemoryManager, MemoryMetadata, MemoryType

        manager = MemoryManager()

        # Test storing a memory
        memory_id = await manager.store_memory(
            user_id="test_user_123",
            memory_type=MemoryType.JOURNAL,
            content="Test journal entry",
            metadata=MemoryMetadata(
                user_id="test_user_123",
                memory_type=MemoryType.JOURNAL,
                importance=MemoryImportance.MEDIUM,
            ),
        )

        assert memory_id is not None
        assert isinstance(memory_id, str)

    @pytest.mark.asyncio
    async def test_memory_retrieval_integration(self, setup_databases):
        """Test memory retrieval with real databases."""
        from app.ai.memory import (
            MemoryImportance,
            MemoryManager,
            MemoryMetadata,
            MemoryRetrievalConfig,
            MemoryType,
        )

        manager = MemoryManager()

        # Store a test memory
        await manager.store_memory(
            user_id="test_user_456",
            memory_type=MemoryType.JOURNAL,
            content="Test journal entry for retrieval",
            metadata=MemoryMetadata(
                user_id="test_user_456",
                memory_type=MemoryType.JOURNAL,
                importance=MemoryImportance.MEDIUM,
            ),
        )

        # Retrieve memories
        config = MemoryRetrievalConfig(max_results=5, enable_ranking=False)
        results = await manager.retrieve_memories(
            user_id="test_user_456",
            query="journal",
            config=config,
        )

        assert isinstance(results, list)


class TestMemorySecurityIntegration:
    """Test memory security integration."""

    @pytest.mark.asyncio
    async def test_user_isolation_enforcement(self, setup_databases):
        """Test that user isolation is enforced across components."""
        from app.ai.memory import MemoryImportance, MemoryManager, MemoryMetadata, MemoryType
        from app.ai.memory.security import MemorySecurityValidator

        manager = MemoryManager()
        MemorySecurityValidator(manager.storage)

        # Store memory for user A
        memory_id_a = await manager.store_memory(
            user_id="user_a",
            memory_type=MemoryType.JOURNAL,
            content="User A's private memory",
            metadata=MemoryMetadata(
                user_id="user_a",
                memory_type=MemoryType.JOURNAL,
                importance=MemoryImportance.HIGH,
            ),
        )

        # Try to retrieve as user B
        memory = await manager.get_memory_by_id(memory_id_a, "user_b")

        # Should return None due to user isolation
        assert memory is None


class TestMemoryWorkflowIntegration:
    """Test complete memory workflow integration."""

    @pytest.mark.asyncio
    async def test_complete_memory_lifecycle(self, setup_databases):
        """Test complete memory lifecycle: create, retrieve, update, delete."""
        from app.ai.memory import MemoryImportance, MemoryManager, MemoryMetadata, MemoryType

        manager = MemoryManager()
        user_id = "workflow_test_user"

        # Create
        memory_id = await manager.store_memory(
            user_id=user_id,
            memory_type=MemoryType.JOURNAL,
            content="Initial content",
            metadata=MemoryMetadata(
                user_id=user_id,
                memory_type=MemoryType.JOURNAL,
                importance=MemoryImportance.MEDIUM,
            ),
        )

        assert memory_id is not None

        # Retrieve
        memory = await manager.get_memory_by_id(memory_id, user_id)
        assert memory is not None
        assert memory.content == "Initial content"

        # Update
        success = await manager.update_memory(
            memory_id=memory_id,
            user_id=user_id,
            updates={"content": "Updated content"},
        )
        assert success is True

        # Verify update
        updated_memory = await manager.get_memory_by_id(memory_id, user_id)
        assert updated_memory.content == "Updated content"

        # Delete
        success = await manager.delete_memory(memory_id, user_id)
        assert success is True

        # Verify deletion
        deleted_memory = await manager.get_memory_by_id(memory_id, user_id)
        assert deleted_memory is None


class TestMemoryRankingIntegration:
    """Test memory ranking integration with real data."""

    @pytest.mark.asyncio
    async def test_ranking_with_multiple_memories(self, setup_databases):
        """Test ranking with multiple memories of different types."""
        from app.ai.memory import (
            MemoryImportance,
            MemoryManager,
            MemoryMetadata,
            MemoryRetrievalConfig,
            MemoryType,
        )

        manager = MemoryManager()
        user_id = "ranking_test_user"

        # Create multiple memories
        memory_types = [MemoryType.JOURNAL, MemoryType.GOAL, MemoryType.HABIT]
        memory_ids = []

        for mem_type in memory_types:
            memory_id = await manager.store_memory(
                user_id=user_id,
                memory_type=mem_type,
                content=f"Test {mem_type.value} content",
                metadata=MemoryMetadata(
                    user_id=user_id,
                    memory_type=mem_type,
                    importance=MemoryImportance.MEDIUM,
                ),
            )
            memory_ids.append(memory_id)

        # Retrieve with ranking
        config = MemoryRetrievalConfig(
            max_results=10,
            enable_ranking=True,
            enable_semantic_search=False,  # Disable for deterministic testing
        )

        results = await manager.retrieve_memories(
            user_id=user_id,
            query="test",
            config=config,
        )

        assert isinstance(results, list)
        # Clean up
        for memory_id in memory_ids:
            await manager.delete_memory(memory_id, user_id)


class TestMemoryBehaviorTrackingIntegration:
    """Test behavior tracking integration."""

    @pytest.mark.asyncio
    async def test_behavior_tracking_workflow(self, setup_databases):
        """Test behavior tracking with memory operations."""
        from app.ai.memory import MemoryImportance, MemoryManager, MemoryMetadata, MemoryType

        manager = MemoryManager()
        user_id = "behavior_test_user"

        # Store a conversation memory (should trigger behavior tracking)
        memory_id = await manager.store_memory(
            user_id=user_id,
            memory_type=MemoryType.CONVERSATION,
            content="Test conversation",
            metadata=MemoryMetadata(
                user_id=user_id,
                memory_type=MemoryType.CONVERSATION,
                importance=MemoryImportance.LOW,
            ),
        )

        # Get behavior summary (now returns Celery task info)
        summary = await manager.get_behavior_summary(user_id)

        assert isinstance(summary, dict)
        # Should return task info instead of actual summary results
        assert "task_id" in summary
        assert summary["status"] == "scheduled"

        # Clean up
        await manager.delete_memory(memory_id, user_id)


class TestMemoryConsolidationIntegration:
    """Test memory consolidation integration."""

    @pytest.mark.asyncio
    async def test_consolidation_workflow(self, setup_databases):
        """Test memory consolidation with similar memories."""
        from app.ai.memory import MemoryImportance, MemoryManager, MemoryMetadata, MemoryType

        manager = MemoryManager()
        user_id = "consolidation_test_user"

        # Create similar memories
        memory_ids = []
        for i in range(3):
            memory_id = await manager.store_memory(
                user_id=user_id,
                memory_type=MemoryType.JOURNAL,
                content=f"Similar journal entry about daily activities {i}",
                metadata=MemoryMetadata(
                    user_id=user_id,
                    memory_type=MemoryType.JOURNAL,
                    importance=MemoryImportance.MEDIUM,
                    tags=["daily", "activities"],
                ),
            )
            memory_ids.append(memory_id)

        # Consolidate memories (now returns Celery task info)
        results = await manager.consolidate_user_memories(
            user_id=user_id,
            memory_type=MemoryType.JOURNAL,
        )

        assert isinstance(results, list)
        # Should return task info instead of actual consolidation results
        assert len(results) > 0
        assert "task_id" in results[0]
        assert results[0]["status"] == "scheduled"

        # Clean up
        for memory_id in memory_ids:
            await manager.delete_memory(memory_id, user_id)


class TestMemoryForgettingIntegration:
    """Test memory forgetting integration."""

    @pytest.mark.asyncio
    async def test_forgetting_policy_application(self, setup_databases):
        """Test applying forgetting policy to memories."""
        from app.ai.memory import MemoryImportance, MemoryManager, MemoryMetadata, MemoryType

        manager = MemoryManager()
        user_id = "forgetting_test_user"

        # Create memories with different importance levels
        memory_ids = []

        # Low importance memory (should be affected by policy)
        low_id = await manager.store_memory(
            user_id=user_id,
            memory_type=MemoryType.JOURNAL,
            content="Low importance temporary note",
            metadata=MemoryMetadata(
                user_id=user_id,
                memory_type=MemoryType.JOURNAL,
                importance=MemoryImportance.TEMPORARY,
            ),
        )
        memory_ids.append(low_id)

        # High importance memory (should be protected)
        high_id = await manager.store_memory(
            user_id=user_id,
            memory_type=MemoryType.JOURNAL,
            content="Critical important information",
            metadata=MemoryMetadata(
                user_id=user_id,
                memory_type=MemoryType.JOURNAL,
                importance=MemoryImportance.CRITICAL,
            ),
        )
        memory_ids.append(high_id)

        # Apply forgetting policy (now returns Celery task info)
        results = await manager.cleanup_user_memories(
            user_id=user_id,
            policy_name="default",
        )

        assert isinstance(results, dict)
        # Should return task info instead of actual cleanup results
        assert "task_id" in results
        assert results["status"] == "scheduled"

        # Verify high importance memory is still accessible
        high_memory = await manager.get_memory_by_id(high_id, user_id)
        assert high_memory is not None

        # Clean up
        for memory_id in memory_ids:
            await manager.delete_memory(memory_id, user_id)
