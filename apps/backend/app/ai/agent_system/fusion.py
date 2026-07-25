# apps/backend/app/ai/agent_system/fusion.py
import logging
from typing import Optional

from app.ai.agent_system.prompts import AGENT_PROMPTS
from app.ai.agent_system.router import AgentRouter
from app.ai.memory_engine import MemoryManager

logger = logging.getLogger(__name__)


class FusionEngine:
    """Fuses memory context, agent routing, and LLM generation for AI responses."""

    def __init__(
        self,
        memory_manager: MemoryManager,
        router: AgentRouter,
        llm_client: Optional[object] = None
    ):
        """
        Initialize the FusionEngine.

        Args:
            memory_manager: MemoryManager instance for context building
            router: AgentRouter instance for query routing
            llm_client: Optional LLM client (Groq/Gemini) for response generation
        """
        self.memory_manager = memory_manager
        self.router = router
        self.llm_client = llm_client

    async def process_user_query(
        self,
        user_id: str,
        query: str,
        query_vector: Optional[list[float]] = None
    ) -> dict:
        """
        Process a user query through the full fusion pipeline.

        Args:
            user_id: Unique identifier for the user
            query: The user's query string
            query_vector: Optional vector embedding of the query for memory retrieval

        Returns:
            Dictionary containing:
                - response: The generated AI response
                - agent_used: The AgentType that handled the query
                - memories_retrieved: Number of memories retrieved from long-term storage
        """
        try:
            # Step 1: Build context from memory
            context = await self.memory_manager.build_context(
                user_id=user_id,
                current_query=query,
                query_vector=query_vector
            )

            chat_history = context.get("chat_history", [])
            # MemoryManager doesn't return memories count, so infer from context
            # If query_vector was provided and system_prompt contains memory info, assume memories were retrieved
            system_prompt = context.get("system_prompt", "")
            memories_retrieved = 1 if query_vector is not None and len(query_vector) > 0 and "memories" in system_prompt.lower() else 0

            # Step 2: Route query to appropriate agent
            selected_agent = self.router.route_query(query, chat_history)

            # Step 3: Assemble system prompt with agent persona and memory context
            base_prompt = AGENT_PROMPTS[selected_agent]
            memory_context = context.get("system_prompt", "")

            # Combine agent prompt with memory context
            if memory_context and memory_context != "You are a helpful AI assistant.":
                full_system_prompt = f"{base_prompt}\n\n{memory_context}"
            else:
                full_system_prompt = base_prompt

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

            logger.info(
                f"Processed query for user {user_id} using {selected_agent.value}, "
                f"retrieved {memories_retrieved} memories"
            )

            # Step 6: Return result
            return {
                "response": response_text,
                "agent_used": selected_agent.value,
                "memories_retrieved": memories_retrieved
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
        """
        Generate a response using the configured LLM client.

        Args:
            system_prompt: The system prompt with agent persona and context
            user_query: The user's current query
            chat_history: Previous conversation history

        Returns:
            The generated response text
        """
        # If no LLM client is configured, return a mock response
        if self.llm_client is None:
            logger.warning("LLM client not configured, using mock response")
            return self._mock_response(system_prompt, user_query)

        try:
            # 1. Start with the system prompt (Agent Persona + Memory Context)
            messages = [{"role": "system", "content": system_prompt}]

            # 2. Append the conversation history
            for msg in chat_history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

            # 3. Add the latest user query
            messages.append({"role": "user", "content": user_query})

            # 4. Generate the response using Groq/OpenAI compatible client
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
        """
        Generate a mock response for testing when LLM is not configured.

        Args:
            system_prompt: The system prompt (used to identify the agent)
            user_query: The user's query

        Returns:
            A mock response string
        """
        # Extract agent type from system prompt for a more contextual mock
        if "Habit Coach" in system_prompt:
            return f"I understand you're asking about: '{user_query}'. As your Habit Coach, I'd help you build sustainable habits through small, consistent actions. Let's start with a tiny habit that takes less than 30 seconds. What existing routine could we anchor this new habit to?"
        elif "Mental Wellness Coach" in system_prompt:
            return f"I hear you're going through something with: '{user_query}'. I'm here to listen and support you. Let's take a moment to breathe together. Can you tell me more about what you're feeling?"
        elif "Fitness Coach" in system_prompt:
            return f"Great question about: '{user_query}'. As your Fitness Coach, I'll help you build a sustainable routine. Let's focus on consistency over intensity. What activities do you currently enjoy, and how many days per week feels realistic?"
        elif "Learning Coach" in system_prompt:
            return f"Excellent topic: '{user_query}'. As your Learning Coach, I'll help you use evidence-based techniques like active recall and spaced repetition. Let's break this down into manageable chunks. What's your main learning goal?"
        elif "Career Coach" in system_prompt:
            return f"Important career question: '{user_query}'. As your Career Coach, I'll help you strategize your professional growth. Let's look at your strengths and where you want to be in 5 years. What skills do you want to develop?"
        elif "Financial Coach" in system_prompt:
            return f"Thanks for asking about: '{user_query}'. As your Financial Coach, I'll help you build healthy money habits. Let's look at your spending patterns together. What's your biggest financial goal right now?"
        elif "Relationship Coach" in system_prompt:
            return f"I understand you're navigating: '{user_query}'. As your Relationship Coach, I'll help you improve communication and build healthier connections. Let's explore this dynamic together. What patterns do you notice?"
        else:  # Life Strategist (default)
            return f"I see you're thinking about: '{user_query}'. As your Life Strategist, I'll help you consider this from a holistic perspective. Let's look at how this aligns with your values and impacts different areas of your life. What matters most to you in this situation?"
