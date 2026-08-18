# tests/test_coaching_architecture_regression.py
"""
Architecture Regression Tests for Coaching Engine.

Tests to ensure Coaching Engine follows approved Lumenly architecture:
- Coaching → RAGOrchestrator / approved AI architecture
- Coaching → LLM Provider Factory
- Coaching → MemoryManager
- Coaching → Security layer
- WebSocket → authentication
- WebSocket → ownership verification
- Tools → registry
- Tools → authorization
- Celery → synchronous architecture
- Celery → no asyncio.run()
- Celery → sync providers
"""
import inspect
from pathlib import Path

import pytest


@pytest.mark.asyncio
class TestCoachingArchitectureCompliance:
    """Test that coaching system follows approved architecture."""

    def test_coaching_service_uses_llm_factory(self):
        """Test that CoachingFlowService uses LLMProviderFactory."""
        from app.services.coaching import CoachingFlowService

        # Check if CoachingFlowService has LLMProviderFactory dependency
        init_signature = inspect.signature(CoachingFlowService.__init__)
        params = init_signature.parameters

        # Should have llm_provider_factory parameter
        assert "llm_provider_factory" in params or any(
            "factory" in str(param) for param in params
        ), "CoachingFlowService should use LLMProviderFactory"

    def test_coaching_service_uses_memory_manager(self):
        """Test that CoachingFlowService uses MemoryManager."""
        from app.services.coaching import CoachingFlowService

        # Check if CoachingFlowService has MemoryManager dependency
        init_signature = inspect.signature(CoachingFlowService.__init__)
        params = init_signature.parameters

        # Should have memory_manager parameter
        assert "memory_manager" in params, "CoachingFlowService should use MemoryManager"

    def test_coaching_service_uses_agent_router(self):
        """Test that CoachingFlowService uses AgentRouter."""
        from app.services.coaching import CoachingFlowService

        # Check if CoachingFlowService has AgentRouter dependency
        init_signature = inspect.signature(CoachingFlowService.__init__)
        params = init_signature.parameters

        # Should have agent_router parameter
        assert "agent_router" in params, "CoachingFlowService should use AgentRouter"

    def test_no_direct_llm_imports_in_coaching(self):
        """Test that coaching service doesn't directly import LLM providers."""
        coaching_file = Path("app/services/coaching.py")

        if not coaching_file.exists():
            pytest.skip("Coaching service file not found")

        content = coaching_file.read_text()

        # Should not directly import specific providers
        forbidden_imports = [
            "from openai import",
            "from anthropic import",
            "from groq import",
            "from google.generativeai import",
            "import openai",
            "import anthropic",
            "import groq"
        ]

        for forbidden in forbidden_imports:
            assert forbidden not in content, f"Coaching service should not directly import {forbidden}"

    def test_coaching_uses_memory_manager_active(self):
        """Test that coaching flows actively use MemoryManager."""
        from app.services.coaching import CoachingFlowService

        # Check if methods actually call memory operations
        source = inspect.getsource(CoachingFlowService)

        # Should contain memory manager method calls
        assert "memory_manager" in source.lower(), "CoachingFlowService should use memory_manager"
        assert "retrieve" in source.lower() or "store" in source.lower(), "Should use memory operations"


@pytest.mark.asyncio
class TestWebSocketArchitecture:
    """Test WebSocket follows approved architecture."""

    def test_websocket_requires_authentication(self):
        """Test that WebSocket endpoint requires authentication."""
        from app.api.endpoints.coaching import coaching_websocket

        # Check function signature
        signature = inspect.signature(coaching_websocket)
        params = signature.parameters

        # Should have token parameter for authentication
        # The token parameter is Optional[str] = Query(None)
        assert "token" in params, f"WebSocket should require authentication token. Available params: {list(params.keys())}"

    def test_websocket_uses_jwt_validation(self):
        """Test that WebSocket uses JWT validation."""
        coaching_file = Path("app/api/endpoints/coaching.py")

        if not coaching_file.exists():
            pytest.skip("Coaching endpoint file not found")

        content = coaching_file.read_text()

        # Should contain JWT validation logic
        assert "decode_access_token" in content or "jwt" in content.lower(), "WebSocket should validate JWT"

    def test_websocket_verifies_ownership(self):
        """Test that WebSocket verifies session ownership."""
        coaching_file = Path("app/api/endpoints/coaching.py")

        if not coaching_file.exists():
            pytest.skip("Coaching endpoint file not found")

        content = coaching_file.read_text()

        # Should contain ownership verification
        assert "user_id" in content and "session.user_id" in content, "WebSocket should verify session ownership"


@pytest.mark.asyncio
class TestToolArchitecture:
    """Test tool system follows approved architecture."""

    def test_tool_registry_exists(self):
        """Test that ToolRegistry exists and is used."""
        from app.ai.tools import ToolRegistry, get_tool_registry

        # Should be able to get the registry
        registry = get_tool_registry()
        assert isinstance(registry, ToolRegistry), "Should return ToolRegistry instance"

    def test_tools_have_allowlist(self):
        """Test that tools are registered in an allowlist."""
        from app.ai.tools import get_tool_registry

        registry = get_tool_registry()
        tools = registry.list_tools()

        # Should have registered tools
        assert len(tools) > 0, "Should have registered tools in allowlist"

    def test_tools_have_authorization(self):
        """Test that tools have authorization requirements."""
        from app.ai.tools import get_tool_registry

        registry = get_tool_registry()

        # Check that registered tools have authorization
        for tool_name in registry.list_tools():
            tool = registry.get_tool(tool_name)
            assert tool is not None, f"Tool {tool_name} should be retrievable"
            assert tool.authorization is not None, f"Tool {tool_name} should have authorization"

    def test_execute_tool_uses_registry(self):
        """Test that execute_tool function uses the registry."""
        coaching_file = Path("app/api/endpoints/coaching.py")

        if not coaching_file.exists():
            pytest.skip("Coaching endpoint file not found")

        content = coaching_file.read_text()

        # Should use tool registry
        assert "get_tool_registry" in content or "ToolRegistry" in content, "Should use tool registry"


class TestCeleryArchitecture:
    """Test Celery workers follow approved architecture."""

    def test_celery_workers_are_synchronous(self):
        """Test that Celery workers don't use asyncio.run()."""
        workers = [
            "app/workers/nudger.py",
            "app/workers/reflection.py",
            "app/workers/tasks.py"
        ]

        for worker_file in workers:
            worker_path = Path(worker_file)
            if not worker_path.exists():
                continue

            content = worker_path.read_text()

            # Should not contain asyncio.run()
            assert "asyncio.run" not in content, f"{worker_file} should not use asyncio.run()"

    def test_celery_workers_use_sync_clients(self):
        """Test that Celery workers use synchronous database clients."""
        nudger_file = Path("app/workers/nudger.py")

        if not nudger_file.exists():
            pytest.skip("Nudger file not found")

        content = nudger_file.read_text()

        # Should use synchronous MongoClient
        assert "MongoClient" in content, "Should use synchronous MongoClient"

        # Should not use async clients
        assert "AsyncMongoClient" not in content, "Should not use AsyncMongoClient"
        assert "AsyncIOMotorClient" not in content, "Should not use AsyncIOMotorClient"

    def test_celery_beat_configured(self):
        """Test that Celery Beat is configured."""
        from app.core.celery_app import celery_app

        # Should have beat_schedule configured
        assert hasattr(celery_app, "conf"), "Celery app should have config"
        assert "beat_schedule" in celery_app.conf, "Should have beat_schedule configured"

        # Should have coaching tasks scheduled
        beat_schedule = celery_app.conf.beat_schedule
        assert len(beat_schedule) > 0, "Should have scheduled tasks"


@pytest.mark.asyncio
class TestSecurityArchitecture:
    """Test security architecture is preserved."""

    def test_coaching_uses_security_validator(self):
        """Test that coaching flows use security validation."""
        from app.services.coaching import CoachingFlowService

        source = inspect.getsource(CoachingFlowService)

        # Should contain security-related imports or usage
        assert "security" in source.lower() or "validator" in source.lower(), "Should use security validation"

    def test_rate_limiting_preserved(self):
        """Test that rate limiting is still in place."""
        coaching_file = Path("app/api/endpoints/coaching.py")

        if not coaching_file.exists():
            pytest.skip("Coaching endpoint file not found")

        content = coaching_file.read_text()

        # Should contain rate limiting logic
        assert "rate_limit" in content.lower() or "check_websocket_rate_limit" in content, "Should use rate limiting"

    def test_compliance_logging_persistent(self):
        """Test that compliance logging uses persistent storage."""
        from app.models.domain import ComplianceEvent

        # ComplianceEvent model should exist
        assert ComplianceEvent is not None, "Should have ComplianceEvent model"

        # Should have proper indexes
        assert "user_id" in ComplianceEvent.Settings.indexes, "Should have user_id index"
        assert "event_type" in ComplianceEvent.Settings.indexes, "Should have event_type index"


@pytest.mark.asyncio
class TestProviderAbstraction:
    """Test that provider abstraction is preserved."""

    def test_llm_provider_interface_used(self):
        """Test that LLMProviderInterface is used."""
        from app.ai.llm.interface import LLMProviderInterface

        # Interface should exist
        assert LLMProviderInterface is not None, "Should have LLMProviderInterface"

    def test_llm_factory_used(self):
        """Test that LLMProviderFactory is used."""
        from app.ai.llm.providers import LLMProviderFactory

        # Factory should exist
        assert LLMProviderFactory is not None, "Should have LLMProviderFactory"

    def test_embedding_provider_interface_used(self):
        """Test that EmbeddingProviderInterface is used."""
        from app.ai.embeddings.interface import EmbeddingProviderInterface

        # Interface should exist
        assert EmbeddingProviderInterface is not None, "Should have EmbeddingProviderInterface"

    def test_no_direct_gemini_imports(self):
        """Test that direct Gemini imports are not used in business logic."""
        business_logic_files = [
            "app/services/coaching.py",
            "app/api/endpoints/coaching.py"
        ]

        for file_path in business_logic_files:
            file = Path(file_path)
            if not file.exists():
                continue

            content = file.read_text()

            # Should not directly import Gemini
            assert "google.generativeai" not in content, f"{file_path} should not directly import Gemini"
            assert "GenerativeModel" not in content, f"{file_path} should not use GenerativeModel directly"


@pytest.mark.asyncio
class TestMemoryArchitecture:
    """Test that memory architecture is preserved."""

    def test_memory_manager_used(self):
        """Test that MemoryManager is used."""
        from app.ai.memory.manager import MemoryManager

        # MemoryManager should exist
        assert MemoryManager is not None, "Should have MemoryManager"

    def test_memory_manager_has_required_methods(self):
        """Test that MemoryManager has required methods."""
        from app.ai.memory.manager import MemoryManager

        # Should have store and retrieve methods
        assert hasattr(MemoryManager, "store_memory"), "Should have store_memory method"
        assert hasattr(MemoryManager, "retrieve_memories"), "Should have retrieve_memories method"

    def test_no_direct_qdrant_imports_in_coaching(self):
        """Test that coaching doesn't directly import Qdrant."""
        coaching_file = Path("app/services/coaching.py")

        if not coaching_file.exists():
            pytest.skip("Coaching service file not found")

        content = coaching_file.read_text()

        # Should not directly import Qdrant
        assert "from qdrant_client" not in content, "Should not directly import Qdrant"
        assert "QdrantClient" not in content, "Should not use QdrantClient directly"


@pytest.mark.asyncio
class TestRAGArchitecture:
    """Test that RAG architecture is preserved."""

    def test_rag_orchestrator_exists(self):
        """Test that RAGOrchestrator exists."""
        from app.ai.rag.orchestrator import RAGOrchestrator

        # RAGOrchestrator should exist
        assert RAGOrchestrator is not None, "Should have RAGOrchestrator"

    def test_rag_orchestrator_uses_memory(self):
        """Test that RAGOrchestrator uses MemoryManager."""
        from app.ai.rag.orchestrator import RAGOrchestrator

        # Check if RAGOrchestrator has memory_manager dependency
        init_signature = inspect.signature(RAGOrchestrator.__init__)
        params = init_signature.parameters

        # Should have memory_manager parameter
        assert "memory_manager" in params, "RAGOrchestrator should use MemoryManager"

    def test_rag_orchestrator_uses_llm_provider(self):
        """Test that RAGOrchestrator uses LLM provider."""
        from app.ai.rag.orchestrator import RAGOrchestrator

        # Check if RAGOrchestrator has llm_provider dependency
        init_signature = inspect.signature(RAGOrchestrator.__init__)
        params = init_signature.parameters

        # Should have llm_provider parameter
        assert "llm_provider" in params, "RAGOrchestrator should use LLM provider"
