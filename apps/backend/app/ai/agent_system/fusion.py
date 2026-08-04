# apps/backend/app/ai/agent_system/fusion.py
import json
import logging
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from app.ai.agent_system.prompts import AGENT_PROMPTS, AgentType
from app.ai.agent_system.router import AgentRouter
from app.ai.memory_engine import MemoryManager

# Import the mock calendar tool definition from Step 2 Choice A
try:
    from app.ai.tools.calendar_tool import CALENDAR_TOOL_DEFINITION, create_calendar_event
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("Step 2 Choice A tool files not found. Tool integration will fail.")
    CALENDAR_TOOL_DEFINITION = {}

logger = logging.getLogger(__name__)


# NEW: A simple schema to parse incoming tool call details from Llama
class ToolCallDetails(BaseModel):
    id: str = Field(..., description="The unique ID of this tool call.")
    name: str = Field(..., description="The name of the function to call.")
    arguments: Dict[str, Any] = Field(..., description="The arguments to pass to the function.")


class FusionEngine:
    """Fuses memory context, agent routing, knowledge retrieval, tool execution, and LLM generation."""

    def __init__(self,
        memory_manager: MemoryManager,
        router: AgentRouter,
        llm_client: Optional[object] = None,
        knowledge_retriever: Optional[object] = None
    ):
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
            # --- 1. Build context & RAG --- (Remains same)
            context = await self.memory_manager.build_context(
                user_id=user_id,
                current_query=query,
                query_vector=query_vector
            )
            chat_history = context.get("chat_history", [])
            system_prompt_memory = context.get("system_prompt", "")

            knowledge_context = ""
            knowledge_snippets_used = 0

            if self.knowledge_retriever:
                # (RAG search logic remains same...)
                kb_results = await self.knowledge_retriever.search_knowledge(user_id=user_id, query=query, top_k=3)
                if kb_results:
                    knowledge_snippets_used = len(kb_results)
                    knowledge_context = "\n\n--- RELEVANT KNOWLEDGE BASE DOCUMENTS ---\n"
                    knowledge_context += "Use the following document snippets to help answer the user's query if they are relevant:\n"
                    for res in kb_results:
                        knowledge_context += f"\n[Source: {res.get('document_title', 'Untitled Document')}]\n{res.get('chunk_text', '')}\n"

            # --- 2. Routing --- (Remains same)
            selected_agent = self.router.route_query(query, chat_history)
            logger.info(f"Routed to: {selected_agent.value}")

            # --- 3. Assemble full system prompt --- (Remains same)
            base_prompt = AGENT_PROMPTS[selected_agent]
            full_system_prompt = base_prompt
            if system_prompt_memory and system_prompt_memory != "You are a helpful AI assistant.":
                full_system_prompt += f"\n\n{system_prompt_memory}"
            if knowledge_context:
                full_system_prompt += f"{knowledge_context}"

            # --- 4. Tool-Aware Generation Logic --- (UPDATED)

            # Define available tools (only provide dummy tool for test scenario to Habit Coach)
            available_tools = None
            if selected_agent == AgentType.HABIT_COACH and CALENDAR_TOOL_DEFINITION:
                logger.info("Equipping Habit Coach with Calendar Tool.")
                available_tools = [CALENDAR_TOOL_DEFINITION]

            # Generate first response (or tool call request)
            response_message, tokens_info = await self._generate_with_tool_support(
                system_prompt=full_system_prompt,
                user_query=query,
                chat_history=chat_history,
                tools=available_tools
            )

            response_text = ""

            # --- 5. Step 2 Orchestration: Handle Tool Execution --- (NEW)
            if response_message.tool_calls:
                logger.info(f"LLM requesting tool calls: {[tc.function.name for tc in response_message.tool_calls]}")

                # Execute tool loop internally to satisfy this test scenario simply
                for tool_call in response_message.tool_calls:
                    if tool_call.function.name == "create_calendar_event":
                        function_name = tool_call.function.name
                        try:
                            # Parse JSON arguments from Llama
                            args = json.loads(tool_call.function.arguments)
                            parsed_details = ToolCallDetails(
                                id=tool_call.id,
                                name=function_name,
                                arguments=args
                            )
                            logger.info(f"Executing mock tool {function_name} for user {user_id}")

                            # Call the mock function created in Choice A
                            # In a real app, this runs the higher-level service
                            mock_result = await create_calendar_event(
                                event_title=parsed_details.arguments.get('event_title'),
                                event_time=parsed_details.arguments.get('event_time')
                            )

                            # 5.1 We need a final confirmation message from the agent.
                            # We feed the tool result back into LLM.
                            response_text = await self._generate_final_agent_confirmation(
                                system_prompt=full_system_prompt,
                                original_query=query,
                                original_chat_history=chat_history,
                                original_tool_call_message=response_message,
                                tool_result=mock_result,
                                tool_call_id=tool_call.id
                            )

                        except json.JSONDecodeError:
                            response_text = "❌ Error parsing function parameters."
                        except Exception as tool_exc:
                            logger.error(f"Function {function_name} failed: {tool_exc}")
                            response_text = f"❌ The {function_name} service is currently unavailable."
            else:
                # Normal response text
                response_text = response_message.content

            # --- 6. Save turn to memory --- (Uses the final response text)
            await self.memory_manager.save_turn(
                user_id=user_id,
                user_query=query,
                assistant_response=response_text
            )

            # --- 7. Return result --- (Stats logic remains same)
            memories_retrieved = 1 if query_vector is not None and len(query_vector) > 0 and "memories" in system_prompt_memory.lower() else 0
            return {
                "response": response_text,
                "agent_used": selected_agent.value,
                "memories_retrieved": memories_retrieved,
                "knowledge_snippets_used": knowledge_snippets_used
            }

        except Exception as e:
            logger.error(f"Failed to process query for user {user_id}: {e}", exc_info=True)
            raise

    # -------------------------------------------------------------
    # UPDATED Groq Generation Helpers
    # -------------------------------------------------------------

    async def _generate_with_tool_support(
        self,
        system_prompt: str,
        user_query: str,
        chat_history: list[dict],
        tools: Optional[list] = None
    ) -> Any: # Returns Groq Choice message object + usage dict
        if self.llm_client is None:
            return None, {}

        try:
            # Build messages array (Groq style)
            messages = [{"role": "system", "content": system_prompt}]
            for msg in chat_history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
            messages.append({"role": "user", "content": user_query})

            # Base parameters
            call_params = {
                "messages": messages,
                "model": "llama-3.3-70b-versatile", # Kept your hardcoded model
                "temperature": 0.7,
                "max_tokens": 1024
            }

            # Inject tools if available
            if tools:
                call_params["tools"] = tools
                call_params["tool_choice"] = "auto" # Decide automatically

            logger.debug(f"Calling Groq Llama with tool capability: {bool(tools)}")
            response = await self.llm_client.chat.completions.create(**call_params)

            return response.choices[0].message, response.usage

        except Exception as e:
            logger.error(f"LLM generation failed in _generate_with_tool_support: {e}", exc_info=True)
            # Mock structure to handle error gracefully within logic flow
            class MockMessage: content = f"Mock error: {e}"; tool_calls = None
            return MockMessage(), {}

    async def _generate_final_agent_confirmation(
        self,
        system_prompt: str,
        original_query: str,
        original_chat_history: list[dict],
        original_tool_call_message: Any, # The message object requesting the tool
        tool_result: str,
        tool_call_id: str
    ) -> str:
        """Calls the LLM again to get the final conversational confirmation after tool success."""
        if self.llm_client is None:
            return "✅ Tool execution complete."

        try:
            # Build the specific orchestration history for Llama to finalize
            orch_history = [{"role": "system", "content": system_prompt}]

            # 1. Past history
            for msg in original_chat_history:
                orch_history.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

            # 2. User original query
            orch_history.append({"role": "user", "content": original_query})

            # 3. Add assistant message REQUESTING the tool call
            orch_history.append(original_tool_call_message)

            # 4. Add the TOOL response message (Result of execution)
            orch_history.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": original_tool_call_message.tool_calls[0].function.name,
                "content": tool_result # Text output of Choice A function
            })

            logger.debug("Calling Groq Llama for final confirmation turn.")

            # Second call: Model now understands the tool SUCCEEDED and provides the final agent wrap-up
            response = await self.llm_client.chat.completions.create(
                messages=orch_history,
                model="llama-3.3-70b-versatile",
                temperature=0.4, # Sightly lower temp for final confirmation
                max_tokens=512
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM final confirmation failed: {e}")
            return f"✅ Action performed, but I had trouble generating a conversational response: {tool_result}"

    def _mock_response(self, system_prompt: str, user_query: str) -> str:
        # Keeping your existing mock just in case llm_client is missing
        return f"Mock response. (If you are seeing this, Step 2 test failed because llm_client is missing)."
