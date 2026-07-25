# apps/backend/app/api/chat.py
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastembed import TextEmbedding

from app.ai.agent_system.fusion import FusionEngine
from app.ai.agent_system.router import AgentRouter
from app.ai.memory_engine import LongTermMemory, MemoryManager, ShortTermMemory
from app.core.config import settings
from app.core.qdrant import get_qdrant_client
from app.core.redis import get_redis_client
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
        
        # Initialize agent router
        agent_router = AgentRouter()
        
        # Initialize LLM client if API keys are available
        llm_client = None
        if settings.GROQ_API_KEY or settings.GEMINI_API_KEY:
            logger.info("LLM API keys detected, LLM client will be used")
            # TODO: Initialize actual Groq/Gemini client here
            # For now, we'll use the mock response in FusionEngine
        else:
            logger.warning("No LLM API keys configured, using mock responses")
        
        # Create FusionEngine
        _fusion_engine = FusionEngine(
            memory_manager=memory_manager,
            router=agent_router,
            llm_client=llm_client
        )
        
        logger.info("FusionEngine initialized successfully")
    
    return _fusion_engine


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a user message through the FusionEngine pipeline.
    
    This endpoint:
    - Receives a user message
    - Initializes or grabs the FusionEngine instance
    - Calls the fusion engine to process the query, inject memory, search knowledge, route to the correct coach
    - Stores the conversation turn
    - Returns a structured response with agent info and memory/knowledge stats
    """
    try:
        # Get FusionEngine instance
        fusion_engine = get_fusion_engine()
        
        # Get embedding model for query vectorization
        embedding_model = get_embedding_model()
        
        # Generate query vector for long-term memory retrieval
        query_vector = list(embedding_model.embed([request.message]))[0]
        
        # Process query through FusionEngine
        result = await fusion_engine.process_user_query(
            user_id=request.user_id,
            query=request.message,
            query_vector=query_vector
        )
        
        # For now, knowledge_snippets_used is not tracked by FusionEngine
        # This would need to be added when knowledge retrieval is integrated
        knowledge_snippets_used = 0
        
        # Return structured response
        return ChatResponse(
            response=result["response"],
            agent_used=result["agent_used"],
            memories_retrieved=result["memories_retrieved"],
            knowledge_snippets_used=knowledge_snippets_used
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process chat request: {str(e)}")
