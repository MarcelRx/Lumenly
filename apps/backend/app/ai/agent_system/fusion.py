# apps/backend/app/ai/agent_system/fusion.py
import logging
from typing import Optional

from app.ai.agent_system.prompts import AGENT_PROMPTS
from app.ai.agent_system.router import AgentRouter
from app.ai.memory_engine import MemoryManager

logger = logging.getLogger(__name__)


class FusionEngine:
    """Fuses memory context, agent routing, knowledge retrieval, and LLM generation for AI responses."""

    def __init__(
        self,
        memory_manager: MemoryManager,
        router: AgentRouter,
        llm_client: Optional[object] = None,
        knowledge_retriever: Optional[object] = None  # Added Knowledge Retriever
    ):
        """
        Initialize the FusionEngine.

        Args:
            memory_manager: MemoryManager instance for context building
            router: AgentRouter instance for query routing
            llm_client: Optional LLM client (Groq/Gemini) for response generation
            knowledge_retriever: Optional KnowledgeRetriever for RAG
        """
        self.memory_manager = memory_manager
        self.router = router
        self.llm_client = llm_client
        self.knowledge_retriever = knowledge_retriever

    async def process_user_query(
        self,
        user_id: str,
        query: str,
        query_vector: Optional[list[float]] = None
    ) -> dict:
        try:
            # Step 1: Build context from memory
            context = await self.memory_manager.build_context(
                user_id=user_id,
                current_query=query,
                query_vector=query_vector
            )

            chat_history = context.get("chat_history", [])
            system_prompt = context.get("system_prompt", "")
            memories_retrieved = 1 if query_vector is not None and len(query_vector) > 0 and "memories" in system_prompt.lower() else 0

            # Step 1.5: Retrieve Knowledge Base Context (RAG)
            knowledge_context = ""
            knowledge_snippets_used = 0

            if self.knowledge_retriever:
                try:
                    kb_results = await self.knowledge_retriever.search_knowledge(
                        user_id=user_id,
                        query=query,
                        top_k=3
                    )

                    if kb_results:
                        knowledge_snippets_used = len(kb_results)
                        knowledge_context = "\n\n--- RELEVANT KNOWLEDGE BASE DOCUMENTS ---\n"
                        knowledge_context += "Use the following document snippets to help answer the user's query if they are relevant:\n"

                        for res in kb_results:
                            title = res.get('document_title', 'Untitled Document')
                            chunk = res.get('chunk_text', '')
                            knowledge_context += f"\n[Source: {title}]\n{chunk}\n"

                        logger.info(f"Retrieved {knowledge_snippets_used} knowledge chunks for user {user_id}")
                except Exception as e:
                    logger.error(f"Knowledge retrieval failed: {e}")

            # Step 2: Route query to appropriate agent
            selected_agent = self.router.route_query(query, chat_history)

            # Step 3: Assemble system prompt with agent persona, memory, and knowledge
            base_prompt = AGENT_PROMPTS[selected_agent]
            memory_context = context.get("system_prompt", "")

            # Combine all contexts together
            full_system_prompt = base_prompt
            if memory_context and memory_context != "You are a helpful AI assistant.":
                full_system_prompt += f"\n\n{memory_context}"
            if knowledge_context:
                full_system_prompt += f"{knowledge_context}"

            # Step 4: Generate response using LLM
            response_text = await self._generate_response(
                system_prompt=full_system_prompt,
                user_query=query,
                chat_history=chat_history
            )

            # Step 5: Save conversation turn to memory
            await self.memory_manager.save_turn(
                user_id=user_id,
                user_query=query,
                assistant_response=response_text
            )

            # Step 6: Return result with RAG stats included
            return {
                "response": response_text,
                "agent_used": selected_agent.value,
                "memories_retrieved": memories_retrieved,
                "knowledge_snippets_used": knowledge_snippets_used
            }

        except Exception as e:
            logger.error(f"Failed to process query for user {user_id}: {e}")
            raise

    async def _generate_response(
        self,
        system_prompt: str,
        user_query: str,
        chat_history: list[dict]
    ) -> str:
        if self.llm_client is None:
            logger.warning("LLM client not configured, using mock response")
            return self._mock_response(system_prompt, user_query)

        try:
            messages = [{"role": "system", "content": system_prompt}]

            for msg in chat_history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

            messages.append({"role": "user", "content": user_query})

            response = await self.llm_client.chat.completions.create(
                messages=messages,
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=1024
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return self._mock_response(system_prompt, user_query)

    def _mock_response(self, system_prompt: str, user_query: str) -> str:
        return f"Mock response. Agent injected successfully. RAG stats updated."
