# apps/backend/app/api/deps.py
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError, PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent_system.router import AgentRouter
from app.ai.embeddings import EmbeddingConfig, EmbeddingProviderFactory, EmbeddingProviderInterface
from app.ai.knowledge_brain.retriever import KnowledgeRetriever
from app.ai.llm import LLMConfig, LLMProviderFactory, LLMProviderInterface
from app.ai.memory_engine import LongTermMemory, MemoryManager, ShortTermMemory
from app.ai.rag.orchestrator import RAGOrchestrator
from app.ai.security import AISecurityValidator, SecurityConfig
from app.core.config import settings
from app.core.security import decode_access_token
from app.db.postgres import get_postgres_session
from app.db.qdrant import get_qdrant_client
from app.db.redis import get_redis_client
from app.models.user import User, UserRole
from app.schemas.user import TokenData
from app.services.coaching import CoachingFlowService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_postgres_session)],
) -> User:
    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        # Only extract user_id from token - email and role must come from database
        token_data = TokenData(id=user_id)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except PyJWTError:
        raise credentials_exception from None

    result = await session.execute(select(User).where(User.id == token_data.id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def require_role(allowed_roles: list[UserRole]):
    """Dependency factory to check if current user has required role."""

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_checker


async def get_llm_provider() -> LLMProviderInterface:
    """Dependency to get the LLM provider based on configuration."""
    # Helper function to check if a key is a placeholder
    def is_placeholder_key(key: str) -> bool:
        if not key:
            return False
        key_lower = key.lower()
        return any(
            pattern in key_lower
            for pattern in [
                "test_",
                "replace_before_production",
                "do_not_use_in_production",
                "mock",
            ]
        )

    # In test environment, always use mock provider to avoid API calls
    if settings.APP_ENV == "test":
        provider_name = "mock"
        api_key = "mock-key"
    elif settings.APP_ENV == "production":
        # In production, NEVER use mock provider
        # Production must use real provider
        groq_key = settings.GROQ_API_KEY.strip() if settings.GROQ_API_KEY else ""
        gemini_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""

        groq_key_valid = groq_key and len(groq_key) > 20 and not is_placeholder_key(groq_key)
        gemini_key_valid = gemini_key and len(gemini_key) > 20 and not is_placeholder_key(gemini_key)

        if groq_key_valid:
            provider_name = "groq"
            api_key = groq_key
        elif gemini_key_valid:
            provider_name = "gemini"
            api_key = gemini_key
        else:
            # Production without valid API keys should fail fast
            raise ValueError(
                "Production environment requires valid GROQ_API_KEY or GEMINI_API_KEY. "
                "Mock provider is not allowed in production."
            )
    else:
        # In development/staging, allow mock provider for testing
        provider_name = "mock"  # Safe default for development
        api_key = "mock-key"

        # Only use real provider if keys are actually set, look real (30+ chars), and are not placeholders
        groq_key = settings.GROQ_API_KEY.strip() if settings.GROQ_API_KEY else ""
        gemini_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""

        if gemini_key and len(gemini_key) >= 30 and not is_placeholder_key(gemini_key):
            provider_name = "gemini"
            api_key = gemini_key
        elif groq_key and len(groq_key) >= 30 and not is_placeholder_key(groq_key):
            provider_name = "groq"
            api_key = groq_key

    # Map provider to model
    model_map = {
        "groq": "llama-3.3-70b-versatile",
        "gemini": settings.GEMINI_MODEL,
        "mock": "mock-model",
    }

    config = LLMConfig(
        provider=provider_name,
        model=model_map.get(provider_name, "mock-model"),
        api_key=api_key,
    )
    provider = LLMProviderFactory.create(config)
    await provider.initialize()
    return provider


async def get_embedding_provider() -> EmbeddingProviderInterface:
    """Dependency to get the embedding provider based on configuration."""
    # In test environment, always use mock provider to avoid API calls
    if settings.APP_ENV == "test":
        provider_name = "mock"
    else:
        # Use configured embedding provider from settings
        provider_name = settings.EMBEDDING_PROVIDER

        # If no API key is configured for the provider, default to mock
        if provider_name == "openai" and not settings.OPENAI_API_KEY:
            provider_name = "mock"
        elif provider_name == "cohere" and not settings.COHERE_API_KEY:
            provider_name = "mock"

    # Map provider to API key
    api_key_map = {
        "openai": settings.OPENAI_API_KEY,
        "cohere": settings.COHERE_API_KEY,
        "fastembed": None,
        "sentence_transformers": None,
        "mock": "mock-key",
    }

    # For mock provider, ensure we use the configured VECTOR_DIMENSION
    # This is critical for tests to match the expected dimension
    config = EmbeddingConfig(
        provider=provider_name,
        model=settings.EMBEDDING_MODEL if provider_name != "mock" else "mock-model",
        api_key=api_key_map.get(provider_name),
        dimension=settings.VECTOR_DIMENSION,  # Always use configured dimension
    )
    provider = EmbeddingProviderFactory.create(config)
    await provider.initialize()
    return provider


async def get_memory_manager() -> MemoryManager:
    """Dependency to get the memory manager."""
    redis_client = get_redis_client()
    qdrant_client = get_qdrant_client()

    short_term = ShortTermMemory(redis_client)
    long_term = LongTermMemory(qdrant_client)

    return MemoryManager(short_term, long_term)


async def get_knowledge_retriever(
    embedding_provider: Annotated[EmbeddingProviderInterface, Depends(get_embedding_provider)],
) -> Optional[KnowledgeRetriever]:
    """Dependency to get the knowledge retriever (optional)."""
    # Knowledge retriever is optional - return None by default
    # The knowledge_base collection may not exist in all environments
    return None


async def get_rag_orchestrator(
    llm_provider: Annotated[LLMProviderInterface, Depends(get_llm_provider)],
    embedding_provider: Annotated[EmbeddingProviderInterface, Depends(get_embedding_provider)],
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
    knowledge_retriever: Annotated[Optional[KnowledgeRetriever], Depends(get_knowledge_retriever)],
) -> RAGOrchestrator:
    """Dependency to get the RAG orchestrator with all required components."""
    security_config = SecurityConfig(
        enable_user_isolation=True,
        enable_prompt_injection_detection=True,
        enable_input_sanitization=True,
        enable_output_filtering=True,
    )
    security_validator = AISecurityValidator(security_config)

    return RAGOrchestrator(
        llm_provider=llm_provider,
        embedding_provider=embedding_provider,
        memory_manager=memory_manager,
        knowledge_retriever=knowledge_retriever,
        security_validator=security_validator,
        max_context_chunks=5,
        min_score_threshold=0.65,
    )


def get_agent_router() -> AgentRouter:
    """Dependency to get the agent router."""
    return AgentRouter()


async def get_coaching_service(
    memory_manager: Annotated[MemoryManager, Depends(get_memory_manager)],
    agent_router: Annotated[AgentRouter, Depends(get_agent_router)],
) -> CoachingFlowService:
    """Dependency to get the coaching flow service with all required components."""
    return CoachingFlowService(
        memory_manager=memory_manager,
        agent_router=agent_router,
        llm_provider_factory=LLMProviderFactory,
    )
