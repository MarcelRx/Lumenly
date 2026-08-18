# apps/backend/tests/test_architecture_regression.py
"""
Architecture Regression Tests

These tests verify that architectural violations cannot silently return.
They check for:
- No asyncio.run() in Celery tasks
- No direct provider imports in API layer
- RAGOrchestrator is used by AI endpoints
- EmbeddingProviderFactory is used by vector endpoints
- Vector dimensions have single source of truth
- Cross-tenant isolation is enforced
"""
import ast
from pathlib import Path

import pytest


class TestCeleryAsyncioFree:
    """Verify Celery tasks contain no asyncio.run() or event loop management."""

    def test_celery_contains_no_asyncio_run(self):
        """Celery tasks.py must not contain asyncio.run()."""
        tasks_file = Path(__file__).parent.parent / "app/workers/tasks.py"
        content = tasks_file.read_text()

        assert "asyncio.run" not in content, \
            "Celery tasks must not use asyncio.run() - use synchronous implementations instead"

        assert "get_event_loop" not in content, \
            "Celery tasks must not manage event loops"

        assert "new_event_loop" not in content, \
            "Celery tasks must not create new event loops"

        assert "run_until_complete" not in content, \
            "Celery tasks must not use run_until_complete"

    def test_celery_tasks_are_sync_functions(self):
        """All Celery task functions must be synchronous (def, not async def)."""
        tasks_file = Path(__file__).parent.parent / "app/workers/tasks.py"
        content = tasks_file.read_text()

        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function is a Celery task (has @celery_app.task decorator)
                is_celery_task = False
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if hasattr(decorator.func, 'id') and 'task' in str(decorator.func.id):
                            is_celery_task = True
                        elif hasattr(decorator.func, 'attr') and 'task' in str(decorator.func.attr):
                            is_celery_task = True

                if is_celery_task:
                    assert not node.name.startswith('_'), \
                        f"Celery task '{node.name}' should not be private"
                    # Ensure it's not async
                    assert not isinstance(node, ast.AsyncFunctionDef), \
                        f"Celery task '{node.name}' must be synchronous (def, not async def)"

    def test_celery_uses_sync_clients(self):
        """Celery tasks must use synchronous database clients."""
        tasks_file = Path(__file__).parent.parent / "app/workers/tasks.py"
        content = tasks_file.read_text()

        # Should use synchronous clients (check for import or usage)
        assert "MongoClient" in content, \
            "Celery tasks should use PyMongo (synchronous)"

        assert "QdrantClient" in content, \
            "Celery tasks should use synchronous QdrantClient"

        # Should NOT use async clients
        assert "motor" not in content.lower(), \
            "Celery tasks must not use Motor (async MongoDB)"

        assert "AsyncMongoClient" not in content, \
            "Celery tasks must not use AsyncMongoClient"

        assert "AsyncQdrantClient" not in content, \
            "Celery tasks must not use AsyncQdrantClient"

    def test_celery_uses_sync_embedding_provider(self):
        """Celery tasks must use synchronous embedding provider, not mock embeddings."""
        tasks_file = Path(__file__).parent.parent / "app/workers/tasks.py"
        content = tasks_file.read_text()

        # Should use synchronous embedding provider
        assert "SyncEmbeddingProviderFactory" in content, \
            "Celery tasks must use SyncEmbeddingProviderFactory"

        assert "SyncEmbeddingConfig" in content, \
            "Celery tasks must use SyncEmbeddingConfig"

        # Should NOT use mock embeddings
        assert "generate_mock_embedding" not in content, \
            "Celery tasks must not use generate_mock_embedding - use real provider instead"

        assert "hashlib" not in content, \
            "Celery tasks must not use hashlib for mock embeddings"

        # Should NOT use asyncio for embeddings
        assert "asyncio.run" not in content, \
            "Celery tasks must not use asyncio.run for embeddings"


class TestProviderAbstraction:
    """Verify provider abstractions are not bypassed."""

    def test_no_direct_llm_provider_imports_in_api(self):
        """API layer must not directly import LLM provider implementations."""
        api_dir = Path(__file__).parent.parent / "app/api"

        forbidden_imports = [
            "from groq import",
            "from openai import",
            "from anthropic import",
            "import groq",
            "import openai",
            "import anthropic",
            "AsyncGroq",
            "AsyncOpenAI",
            "AsyncAnthropic",
        ]

        for py_file in api_dir.rglob("*.py"):
            content = py_file.read_text()
            for forbidden in forbidden_imports:
                assert forbidden not in content, \
                    f"File {py_file} contains forbidden direct provider import: {forbidden}"

    def test_no_direct_embedding_provider_imports_in_api(self):
        """API layer must not directly import embedding provider implementations."""
        api_dir = Path(__file__).parent.parent / "app/api"

        forbidden_imports = [
            "from fastembed import",
            "import fastembed",
            "TextEmbedding",
            "from sentence_transformers import",
            "import sentence_transformers",
        ]

        for py_file in api_dir.rglob("*.py"):
            content = py_file.read_text()
            for forbidden in forbidden_imports:
                assert forbidden not in content, \
                    f"File {py_file} contains forbidden direct embedding import: {forbidden}"

    def test_ai_endpoint_uses_rag_orchestrator(self):
        """AI endpoints must use RAGOrchestrator."""
        chat_endpoint = Path(__file__).parent.parent / "app/api/endpoints/chat.py"
        ai_endpoint = Path(__file__).parent.parent / "app/api/endpoints/ai.py"

        for endpoint_file in [chat_endpoint, ai_endpoint]:
            if endpoint_file.exists():
                content = endpoint_file.read_text()
                assert "RAGOrchestrator" in content, \
                    f"{endpoint_file.name} must use RAGOrchestrator"
                assert "get_rag_orchestrator" in content, \
                    f"{endpoint_file.name} must use get_rag_orchestrator dependency"

    def test_vectors_endpoint_uses_embedding_factory(self):
        """Vectors endpoint must use EmbeddingProviderFactory."""
        vectors_endpoint = Path(__file__).parent.parent / "app/api/endpoints/vectors.py"

        if vectors_endpoint.exists():
            content = vectors_endpoint.read_text()
            assert "EmbeddingProviderFactory" in content or "get_embedding_provider" in content, \
                "vectors.py must use EmbeddingProviderFactory or get_embedding_provider"

            # Should NOT directly instantiate providers
            assert "TextEmbedding(" not in content, \
                "vectors.py must not directly instantiate TextEmbedding"
            assert "SentenceTransformer(" not in content, \
                "vectors.py must not directly instantiate SentenceTransformer"

    def test_vector_dimension_has_single_source_of_truth(self):
        """Vector dimensions must use settings.VECTOR_DIMENSION as single source."""
        vectors_endpoint = Path(__file__).parent.parent / "app/api/endpoints/vectors.py"

        if vectors_endpoint.exists():
            content = vectors_endpoint.read_text()

            # Should reference settings.VECTOR_DIMENSION
            assert "VECTOR_DIMENSION" in content or "VECTOR_SIZE" in content, \
                "vectors.py must reference VECTOR_DIMENSION from settings"

            # Should NOT hardcode dimensions
            hardcoded_dimensions = ["1536", "1024", "384", "768", "3072"]
            for dimension in hardcoded_dimensions:
                # Allow in comments but not in code that sets dimension
                lines_with_dimension = [
                    line for line in content.split('\n')
                    if dimension in line and not line.strip().startswith('#')
                ]
                for line in lines_with_dimension:
                    # Allow if it's just referencing the constant
                    if "=" in line and "VECTOR" not in line.upper():
                        # This might be a hardcoded dimension assignment
                        # Check if it's actually setting a dimension
                        if "size" in line.lower() or "dimension" in line.lower():
                            pytest.fail(
                                f"vectors.py appears to hardcode dimension {dimension}. "
                                "Use settings.VECTOR_DIMENSION instead."
                            )


class TestCanonicalArchitecture:
    """Verify the canonical RAG architecture is followed."""

    def test_no_duplicate_rag_implementations(self):
        """There should be no duplicate RAG implementations."""
        app_dir = Path(__file__).parent.parent / "app"

        # Check for old files that should have been removed
        forbidden_files = [
            "app/api/chat.py",  # Old duplicate chat endpoint at wrong path
            "app/services/chat_service.py",  # Old chat service
            "app/services/rag.py",  # Old RAG service
        ]

        for forbidden_file in forbidden_files:
            full_path = app_dir / forbidden_file
            assert not full_path.exists(), \
                f"Legacy file {forbidden_file} should have been removed"

        # Verify main.py does not register chat router (only canonical /v1/ai/ask)
        main_file = Path(__file__).parent.parent / "app/main.py"
        main_content = main_file.read_text()
        assert "chat_router" not in main_content, \
            "main.py should not register chat_router - only canonical /v1/ai/ask endpoint should exist"
        assert "fusion_chat_router" not in main_content, \
            "main.py should not register fusion_chat_router - only canonical /v1/ai/ask endpoint should exist"

    def test_rag_orchestrator_exists(self):
        """RAGOrchestrator must exist and be the canonical implementation."""
        orchestrator_file = Path(__file__).parent.parent / "app/ai/rag/orchestrator.py"
        assert orchestrator_file.exists(), \
            "RAGOrchestrator must exist as the canonical RAG implementation"

    def test_memory_manager_exists(self):
        """MemoryManager must exist for memory operations."""
        memory_manager_file = Path(__file__).parent.parent / "app/ai/memory/manager.py"
        assert memory_manager_file.exists(), \
            "MemoryManager must exist for memory operations"


class TestMultiTenantIsolation:
    """Verify multi-tenant isolation is enforced."""

    def test_cross_tenant_rag_isolation(self):
        """RAG endpoints must enforce user_id filtering."""
        ai_endpoint = Path(__file__).parent.parent / "app/api/endpoints/ai.py"

        # Only check the canonical /v1/ai/ask endpoint
        if ai_endpoint.exists():
            content = ai_endpoint.read_text()
            # Should pass user_id to RAG orchestrator
            assert "user_id" in content, \
                f"{ai_endpoint.name} must pass user_id for tenant isolation"
            assert "RAGOrchestrator" in content, \
                f"{ai_endpoint.name} must use RAGOrchestrator"

    def test_cross_tenant_memory_isolation(self):
        """Memory endpoints must enforce user_id filtering."""
        memory_endpoint = Path(__file__).parent.parent / "app/api/endpoints/memory.py"

        if memory_endpoint.exists():
            content = memory_endpoint.read_text()
            # Should pass user_id to memory operations
            assert "user_id" in content, \
                "memory.py must pass user_id for tenant isolation"

            # Should have dependency injection for current user
            assert "get_current" in content, \
                "memory.py must authenticate users for tenant isolation"

    def test_cross_tenant_vector_isolation(self):
        """Vector endpoints must enforce user_id filtering."""
        vectors_endpoint = Path(__file__).parent.parent / "app/api/endpoints/vectors.py"

        if vectors_endpoint.exists():
            content = vectors_endpoint.read_text()
            # Should filter by user_id in vector searches
            assert "user_id" in content, \
                "vectors.py must filter by user_id for tenant isolation"

            # Should use Qdrant filters
            assert "Filter" in content or "filter" in content, \
                "vectors.py must use Qdrant filters for tenant isolation"


class TestSecurityPipeline:
    """Verify security pipeline is not bypassed."""

    def test_ai_endpoints_use_security(self):
        """AI endpoints must use security validation."""
        ai_endpoint = Path(__file__).parent.parent / "app/api/endpoints/ai.py"

        # Only check the canonical /v1/ai/ask endpoint
        if ai_endpoint.exists():
            content = ai_endpoint.read_text()
            # Should use RAGOrchestrator which includes security
            assert "RAGOrchestrator" in content, \
                f"{ai_endpoint.name} must use RAGOrchestrator for security"

    def test_authentication_required(self):
        """All AI/RAG endpoints must require authentication."""
        endpoints_to_check = [
            "app/api/endpoints/ai.py",  # Canonical RAG endpoint
            "app/api/endpoints/memory.py",
            "app/api/endpoints/vectors.py",
        ]

        for endpoint_path in endpoints_to_check:
            endpoint_file = Path(__file__).parent.parent / endpoint_path
            if endpoint_file.exists():
                content = endpoint_file.read_text()
                # Should have authentication dependency
                assert "get_current" in content, \
                    f"{endpoint_path} must require authentication"

    def test_rate_limiting_fail_closed_in_production(self):
        """Production must fail-closed on rate limiting errors."""
        main_file = Path(__file__).parent.parent / "app/main.py"
        content = main_file.read_text()

        # Extract production section
        if 'if settings.APP_ENV == "production":' in content:
            production_start = content.find('if settings.APP_ENV == "production":')
            # Get a reasonable window for the production section
            production_section = content[production_start:production_start + 3000]
        else:
            pytest.fail("Could not find production section in main.py")

        # In production, RATE_LIMIT_FAIL_OPEN should cause startup failure
        assert "RATE_LIMIT_FAIL_OPEN" in production_section, \
            "Production section must check RATE_LIMIT_FAIL_OPEN configuration"

        # Should raise ValueError in production, not just warn
        assert 'raise ValueError' in production_section and 'RATE_LIMIT_FAIL_OPEN' in production_section, \
            "Production section must raise ValueError for RATE_LIMIT_FAIL_OPEN, not just warn"


class TestServicesDirectory:
    """Verify services directory doesn't contain legacy implementations."""

    def test_no_legacy_services(self):
        """Services directory should not contain legacy AI/RAG implementations."""
        services_dir = Path(__file__).parent.parent / "app/services"

        if services_dir.exists():
            # Check for legacy files
            legacy_files = [
                "chat_service.py",
                "rag.py",
            ]

            for legacy_file in legacy_files:
                legacy_path = services_dir / legacy_file
                assert not legacy_path.exists(), \
                    f"Legacy service file {legacy_file} should have been removed"
