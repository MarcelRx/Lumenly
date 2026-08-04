# apps/backend/app/api/chat.py
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastembed import TextEmbedding
from groq import AsyncGroq

from app.ai.agent_system.fusion import FusionEngine
from app.ai.agent_system.router import AgentRouter
from app.ai.knowledge_brain.retriever import KnowledgeRetriever
from app.ai.memory_engine import LongTermMemory, MemoryManager, ShortTermMemory
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.qdrant import get_qdrant_client
from app.core.redis import get_redis_client
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

# Global instances for singleton pattern
_fusion_engine: Optional[FusionEngine] = None
_embedding_model: Optional[TextEmbedding] = None


def get_embedding_model() -> TextEmbedding:
    """Get or initialize the embedding model."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Initializing fastembed embedding model...")
        _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        logger.info("Fastembed embedding model initialized")
    return _embedding_model


async def async_embed_func(text: str) -> list[float]:
    """
    Async wrapper for the FastEmbed model.
    Required because KnowledgeRetriever expects an awaitable embedding function.
    """
    model = get_embedding_model()
    # FastEmbed returns a generator of numpy arrays. Extract the first and convert to standard list.
    embedding = list(model.embed([text]))[0]
    return embedding.tolist()


def get_fusion_engine() -> FusionEngine:
    """Get or initialize the FusionEngine with all dependencies."""
    global _fusion_engine
    if _fusion_engine is None:
        logger.info("Initializing FusionEngine...")

        # Get clients
        redis_client = get_redis_client()
        qdrant_client = get_qdrant_client()

        # Initialize memory components
        short_term = ShortTermMemory(redis_client)
        long_term = LongTermMemory(qdrant_client)
        memory_manager = MemoryManager(short_term, long_term)

        # Initialize knowledge retriever
        knowledge_retriever = KnowledgeRetriever(
            qdrant_client=qdrant_client,
            embed_func=async_embed_func
        )

        # Initialize agent router
        agent_router = AgentRouter()

        # Initialize LLM client using Groq
        llm_client = None
        if settings.GROQ_API_KEY:
            logger.info("Groq API key detected, initializing AsyncGroq client")
            llm_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        else:
            logger.warning("No LLM API keys configured, using mock responses")

        # Create FusionEngine, now with Knowledge Retrieval attached!
        _fusion_engine = FusionEngine(
            memory_manager=memory_manager,
            router=agent_router,
            llm_client=llm_client,
            knowledge_retriever=knowledge_retriever
        )

        logger.info("FusionEngine initialized successfully")

    return _fusion_engine


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
) -> ChatResponse:
    """
    Process a user message through the FusionEngine pipeline.
    """
    try:
        # Get FusionEngine instance
        fusion_engine = get_fusion_engine()

        # Get embedding model for query vectorization
        embedding_model = get_embedding_model()

        # Generate query vector for long-term memory retrieval
        query_vector = list(embedding_model.embed([request.message]))[0].tolist()

        # Process query through FusionEngine
        result = await fusion_engine.process_user_query(
            user_id=str(current_user.id),
            query=request.message,
            query_vector=query_vector
        )

        # Return structured response (now dynamically passing knowledge stats!)
        return ChatResponse(
            response=result["response"],
            agent_used=result["agent_used"],
            memories_retrieved=result["memories_retrieved"],
            knowledge_snippets_used=result.get("knowledge_snippets_used", 0)
        )

    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process chat request: {str(e)}")
