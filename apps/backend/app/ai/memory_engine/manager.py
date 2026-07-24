# apps/backend/app/ai/memory_engine/manager.py
import logging
from typing import Optional

from app.ai.memory_engine.short_term import ShortTermMemory
from app.ai.memory_engine.long_term import LongTermMemory

logger = logging.getLogger(__name__)


class MemoryManager:
    """Orchestrates short-term and long-term memory for AI context building."""
    
    def __init__(
        self,
        short_term: ShortTermMemory,
        long_term: LongTermMemory
    ):
        self.short_term = short_term
        self.long_term = long_term
    
    async def build_context(
        self,
        user_id: str,
        current_query: str,
        query_vector: Optional[list[float]] = None
    ) -> dict:
        """
        Gathers recent chat history and relevant long-term memories.
        
        Args:
            user_id: Unique identifier for the user
            current_query: The current user query
            query_vector: Optional vector embedding of the query for long-term memory retrieval
            
        Returns:
            Dictionary with "system_prompt" and "chat_history" keys
        """
        try:
            # Retrieve short-term chat history
            chat_history = await self.short_term.get_history(user_id)
            
            # Retrieve relevant long-term memories if query_vector is provided
            relevant_memories = []
            if query_vector:
                relevant_memories = await self.long_term.retrieve_relevant(
                    user_id=user_id,
                    query_vector=query_vector,
                    top_k=3
                )
            
            # Build system prompt with relevant memories
            system_prompt = "You are a helpful AI assistant."
            if relevant_memories:
                memories_text = "\n".join([f"- {mem}" for mem in relevant_memories])
                system_prompt = (
                    f"You are a helpful AI assistant. "
                    f"Here are some relevant past memories about this user:\n{memories_text}"
                )
            
            logger.debug(
                f"Built context for user {user_id}: "
                f"{len(chat_history)} chat messages, {len(relevant_memories)} relevant memories"
            )
            
            return {
                "system_prompt": system_prompt,
                "chat_history": chat_history
            }
            
        except Exception as e:
            logger.error(f"Failed to build context for user {user_id}: {e}")
            # Return empty context on error
            return {
                "system_prompt": "You are a helpful AI assistant.",
                "chat_history": []
            }
    
    async def save_turn(
        self,
        user_id: str,
        user_query: str,
        assistant_response: str
    ) -> None:
        """
        Saves a conversation turn (user query and assistant response) to short-term memory.
        
        Args:
            user_id: Unique identifier for the user
            user_query: The user's message
            assistant_response: The assistant's response
        """
        try:
            # Save user message
            await self.short_term.add_message(
                user_id=user_id,
                role="user",
                content=user_query
            )
            
            # Save assistant message
            await self.short_term.add_message(
                user_id=user_id,
                role="assistant",
                content=assistant_response
            )
            
            logger.debug(f"Saved conversation turn for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to save conversation turn for user {user_id}: {e}")
            raise
