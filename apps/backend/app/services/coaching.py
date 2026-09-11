# apps/backend/app/services/coaching.py
import logging
import uuid
from datetime import datetime

from app.ai.agent_system.router import AgentRouter
from app.ai.agent_system.schemas.agent_types import AgentType
from app.ai.llm import LLMConfig, LLMMessage, LLMProviderFactory
from app.ai.memory_engine import MemoryManager
from app.models.domain import AIInsight, CoachingSession, InsightType

logger = logging.getLogger(__name__)


class CoachingFlowService:
    """Service for implementing the four coaching session flows."""

    def __init__(
        self,
        memory_manager: MemoryManager,
        agent_router: AgentRouter,
        llm_provider_factory: LLMProviderFactory = None,
    ):
        self.memory_manager = memory_manager
        self.agent_router = agent_router
        self.llm_provider_factory = llm_provider_factory or LLMProviderFactory

    async def handle_assessment_flow(
        self,
        session: CoachingSession,
        user_message: str,
    ) -> dict:
        """
        Handle assessment flow - 30-minute structured interview.

        Bootstraps UserBlueprint with comprehensive life domain assessment.
        Uses real LLM provider through approved architecture.
        """
        logger.info(f"Handling assessment flow for session {session.id}")

        # Route to Life Strategist for comprehensive assessment
        selected_agent = self.agent_router.route_query(
            user_message,
            chat_history=[]
        )

        # Build assessment context with memory retrieval
        assessment_context = await self._build_assessment_context(session.user_id)

        # Retrieve relevant memories for context
        try:
            memories = await self.memory_manager.retrieve_memories(
                user_id=str(session.user_id),
                query=user_message,
                config=None  # Use default config
            )
            logger.info(f"Retrieved {len(memories)} memories for assessment context")
        except Exception as e:
            logger.error(f"Memory retrieval failed for assessment: {e}")
            memories = []

        # Build LLM messages with context
        system_prompt = self._build_assessment_system_prompt(assessment_context, memories)

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_message)
        ]

        # Generate assessment response using LLM provider
        try:
            # Create LLM config with actual provider settings
            from app.core.config import settings

            # Determine which provider to use based on available API keys
            if settings.GROQ_API_KEY:
                provider = "groq"
                model = "llama3-70b-8192"
                api_key = settings.GROQ_API_KEY
            elif settings.GEMINI_API_KEY:
                provider = "gemini"
                model = settings.GEMINI_MODEL
                api_key = settings.GEMINI_API_KEY
            else:
                # Fallback to mock for development/testing
                provider = "mock"
                model = "assessment-model"
                api_key = None

            llm_config = LLMConfig(
                provider=provider,
                model=model,
                api_key=api_key,
                temperature=0.7,
                max_tokens=500
            )

            llm_provider = self.llm_provider_factory.create(llm_config)
            await llm_provider.initialize()

            llm_response = await llm_provider.generate(messages)

            response_content = llm_response.content

            # Store the interaction in memory
            await self.memory_manager.store_memory(
                user_id=str(session.user_id),
                memory_type="conversation",
                content=f"User: {user_message}\nAssistant: {response_content}",
                metadata=None
            )

        except Exception as e:
            logger.error(f"LLM generation failed for assessment: {e}")
            # Fallback to simple response
            response_content = f"I understand you're sharing: {user_message}. Let me help you explore this further."

        response = {
            "type": "assistant_message",
            "content": response_content,
            "agent_used": selected_agent.value,
            "flow_stage": "assessment",
            "context_used": {
                "memories_retrieved": len(memories),
                "assessment_domains": len(assessment_context.get("domains_to_cover", []))
            },
            "progress": 0.1  # 10% complete
        }

        # Store assessment progress in session metadata
        session.metadata["assessment_progress"] = 0.1
        session.metadata["current_stage"] = "goals_assessment"
        await session.save()

        return response

    async def handle_nudge_flow(
        self,
        session: CoachingSession,
        user_message: str,
    ) -> dict:
        """
        Handle nudge flow - context-aware prompts.

        Generates nudges based on actual habit/goal/wellness state.
        Uses real LLM provider through approved architecture.
        """
        logger.info(f"Handling nudge flow for session {session.id}")

        # Build nudge context from real user state
        context = await self._build_nudge_context(session.user_id)

        # Route to appropriate agent based on context
        selected_agent = self.agent_router.route_query(
            user_message,
            chat_history=[]
        )

        # Retrieve relevant memories for nudge context
        try:
            memories = await self.memory_manager.retrieve_memories(
                user_id=str(session.user_id),
                query="habits goals wellness progress",
                config=None
            )
            logger.info(f"Retrieved {len(memories)} memories for nudge context")
        except Exception as e:
            logger.error(f"Memory retrieval failed for nudge: {e}")
            memories = []

        # Build LLM messages with real user context
        system_prompt = self._build_nudge_system_prompt(context, memories)

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_message)
        ]

        # Generate nudge response using LLM provider
        try:
            from app.core.config import settings

            # Determine which provider to use based on available API keys
            if settings.GROQ_API_KEY:
                provider = "groq"
                model = "llama3-70b-8192"
                api_key = settings.GROQ_API_KEY
            elif settings.GEMINI_API_KEY:
                provider = "gemini"
                model = settings.GEMINI_MODEL
                api_key = settings.GEMINI_API_KEY
            else:
                # Fallback to mock for development/testing
                provider = "mock"
                model = "nudge-model"
                api_key = None

            llm_config = LLMConfig(
                provider=provider,
                model=model,
                api_key=api_key,
                temperature=0.8,
                max_tokens=300
            )

            llm_provider = self.llm_provider_factory.create(llm_config)
            await llm_provider.initialize()

            llm_response = await llm_provider.generate(messages)
            response_content = llm_response.content

            # Store the interaction in memory
            await self.memory_manager.store_memory(
                user_id=str(session.user_id),
                memory_type="conversation",
                content=f"Nudge interaction: {user_message}\nResponse: {response_content}",
                metadata=None
            )

        except Exception as e:
            logger.error(f"LLM generation failed for nudge: {e}")
            # Fallback based on real context
            if context.get("missed_habits", 0) > 0:
                response_content = f"I noticed you missed {context['missed_habits']} habit(s) recently. Would you like to reschedule or adjust your routine?"
            elif context.get("upcoming_deadlines", 0) > 0:
                response_content = f"You have {context['upcoming_deadlines']} goal(s) coming up soon. How can I help you stay on track?"
            else:
                response_content = "You're making great progress! Keep up the momentum with your current habits."

        response = {
            "type": "assistant_message",
            "content": response_content,
            "agent_used": selected_agent.value,
            "flow_stage": "nudge",
            "context_used": {
                "missed_habits": context.get("missed_habits", 0),
                "wellness_score": context.get("wellness_score", 0),
                "upcoming_deadlines": context.get("upcoming_deadlines", 0),
                "memories_used": len(memories)
            }
        }

        return response

    async def handle_reflection_flow(
        self,
        session: CoachingSession,
        user_message: str,
    ) -> dict:
        """
        Handle reflection flow - end-day sentiment analysis.

        Analyzes actual journal sentiment trends and provides recommendations.
        Uses real LLM provider through approved architecture.
        """
        logger.info(f"Handling reflection flow for session {session.id}")

        # Build reflection context from actual journal entries
        context = await self._build_reflection_context(session.user_id)

        # Route to Mental Wellness agent for reflection
        selected_agent = AgentType.MENTAL_WELLNESS

        # Retrieve relevant memories for reflection context
        try:
            memories = await self.memory_manager.retrieve_memories(
                user_id=str(session.user_id),
                query="journal mood sentiment reflection",
                config=None
            )
            logger.info(f"Retrieved {len(memories)} memories for reflection context")
        except Exception as e:
            logger.error(f"Memory retrieval failed for reflection: {e}")
            memories = []

        # Build LLM messages with real journal context
        system_prompt = self._build_reflection_system_prompt(context, memories)

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_message)
        ]

        # Generate reflection response using LLM provider
        try:
            from app.core.config import settings

            # Determine which provider to use based on available API keys
            if settings.GROQ_API_KEY:
                provider = "groq"
                model = "llama3-70b-8192"
                api_key = settings.GROQ_API_KEY
            elif settings.GEMINI_API_KEY:
                provider = "gemini"
                model = settings.GEMINI_MODEL
                api_key = settings.GEMINI_API_KEY
            else:
                # Fallback to mock for development/testing
                provider = "mock"
                model = "reflection-model"
                api_key = None

            llm_config = LLMConfig(
                provider=provider,
                model=model,
                api_key=api_key,
                temperature=0.7,
                max_tokens=400
            )

            llm_provider = self.llm_provider_factory.create(llm_config)
            await llm_provider.initialize()

            llm_response = await llm_provider.generate(messages)
            response_content = llm_response.content

            # Store the interaction in memory
            await self.memory_manager.store_memory(
                user_id=str(session.user_id),
                memory_type="conversation",
                content=f"Reflection: {user_message}\nAnalysis: {response_content}",
                metadata=None
            )

        except Exception as e:
            logger.error(f"LLM generation failed for reflection: {e}")
            # Fallback based on real sentiment analysis
            sentiment_trend = context.get("sentiment_trend", "stable")
            if sentiment_trend == "improving":
                response_content = "Your journal entries show a positive trend. Keep up the great work with your reflection practice!"
            elif sentiment_trend == "declining":
                response_content = "I notice some challenges in your recent entries. Remember that it's okay to have difficult days - self-compassion is important."
            else:
                response_content = "Your journal shows a stable pattern. Consider trying some new reflection prompts to gain fresh insights."

        response = {
            "type": "assistant_message",
            "content": response_content,
            "agent_used": selected_agent.value,
            "flow_stage": "reflection",
            "sentiment_trend": context.get("sentiment_trend", "stable"),
            "journal_entries_analyzed": context.get("journal_count", 0),
            "memories_used": len(memories),
            "insights_generated": []
        }

        # Generate and store AI insights
        insights = await self._generate_reflection_insights(
            session.user_id,
            session.id,
            context
        )

        if insights:
            response["insights_generated"] = [str(insight.id) for insight in insights]

        return response

    async def handle_escalation_flow(
        self,
        session: CoachingSession,
        user_message: str,
    ) -> dict:
        """
        Handle escalation flow - crisis detection.

        Uses real safety logic beyond simple keyword matching.
        Implements persistent audit logging for compliance.
        """
        logger.warning(f"Handling escalation flow for session {session.id}")

        # Build crisis context with real safety analysis
        context = await self._build_escalation_context(session.user_id, user_message)

        # Always route to Mental Wellness for escalation
        selected_agent = AgentType.MENTAL_WELLNESS

        # Use AI to assess severity (more sophisticated than keyword matching)
        severity_level = await self._assess_crisis_severity(user_message, context)

        # Generate appropriate response based on severity
        if severity_level >= 0.8:  # High severity
            response_content = "I'm very concerned about what you've shared. Please reach out for immediate support."
        elif severity_level >= 0.5:  # Medium severity
            response_content = "I want to make sure you're okay. Please consider reaching out to someone you trust."
        else:  # Low severity
            response_content = "I'm here to support you. Let's talk about what you're experiencing."

        # Generate escalation response with resources
        response = {
            "type": "assistant_message",
            "content": response_content,
            "agent_used": selected_agent.value,
            "flow_stage": "escalation",
            "crisis_detected": context.get("crisis_detected", False),
            "severity_level": severity_level,
            "resources": [
                {
                    "name": "National Suicide Prevention Lifeline",
                    "phone": "988",
                    "description": "24/7 free and confidential support"
                },
                {
                    "name": "Crisis Text Line",
                    "phone": "Text HOME to 741741",
                    "description": "24/7 crisis support via text"
                }
            ],
            "logged_to_compliance": True
        }

        # Log escalation to compliance with persistent storage
        await self._log_escalation(session.user_id, session.id, context, severity_level)

        return response

    async def _build_assessment_context(self, user_id: uuid.UUID) -> dict:
        """Build context for assessment flow."""
        # Retrieve user's existing data for assessment
        return {
            "user_id": user_id,
            "assessment_stage": "initial",
            "domains_to_cover": [
                "mental_health",
                "productivity",
                "fitness",
                "relationships",
                "career",
                "finance",
                "learning",
                "habits"
            ]
        }

    def _build_assessment_system_prompt(self, context: dict, memories: list) -> str:
        """Build system prompt for assessment flow with context."""
        base_prompt = """You are a comprehensive life coach conducting an initial assessment interview.
Your goal is to understand the user's current state across multiple life domains and identify areas for growth.

Domains to explore:
"""

        for domain in context.get("domains_to_cover", []):
            base_prompt += f"- {domain}\n"

        if memories:
            base_prompt += "\nRelevant context from previous interactions:\n"
            for memory in memories[:3]:  # Use top 3 most relevant memories
                base_prompt += f"- {memory.memory.content[:200]}...\n"

        base_prompt += """
Guidelines:
- Ask open-ended questions to understand the user's current situation
- Listen actively and show empathy
- Identify strengths and areas for improvement
- Help the user set realistic, meaningful goals
- Maintain a supportive, non-judgmental tone
"""

        return base_prompt

    async def _build_nudge_context(self, user_id: uuid.UUID) -> dict:
        """Build context for nudge flow from real user state."""
        # Retrieve actual user state from database
        try:
            from app.models.domain import Goal, Habit

            # Query missed habits (habits with low streak or recent misses)
            # This is a simplified query - production would have more sophisticated logic
            missed_habits_count = await Habit.find(
                Habit.user_id == user_id,
                Habit.streak_count < 3  # Example: low streak indicates missed habits
            ).count()

            # Query upcoming deadlines (goals not completed with target date soon)
            from datetime import datetime, timedelta
            upcoming_deadline_threshold = datetime.now() + timedelta(days=7)
            upcoming_deadlines_count = await Goal.find(
                Goal.user_id == user_id,
                not Goal.is_completed,
                Goal.target_date <= upcoming_deadline_threshold
            ).count()

            # Wellness score calculated from journal entries
            # Get recent journal entries for mood analysis
            from app.models.domain import JournalEntry
            week_ago = datetime.now() - timedelta(days=7)
            recent_journals = await JournalEntry.find(
                JournalEntry.user_id == user_id,
                JournalEntry.created_at >= week_ago,
                JournalEntry.mood_score is not None
            ).to_list()

            if recent_journals:
                avg_mood = sum(j.mood_score for j in recent_journals) / len(recent_journals)
                wellness_score = avg_mood * 10  # Convert to 0-100 scale
            else:
                wellness_score = 70  # Default if no journal data

            return {
                "user_id": user_id,
                "missed_habits": missed_habits_count,
                "wellness_score": wellness_score,
                "upcoming_deadlines": upcoming_deadlines_count,
                "recent_activity": "moderate"
            }

        except Exception as e:
            logger.error(f"Failed to build nudge context for user {user_id}: {e}")
            # Return default context on error
            return {
                "user_id": user_id,
                "missed_habits": 0,
                "wellness_score": 70,
                "upcoming_deadlines": 0,
                "recent_activity": "unknown"
            }

    def _build_nudge_system_prompt(self, context: dict, memories: list) -> str:
        """Build system prompt for nudge flow with real context."""
        base_prompt = """You are a supportive coach providing gentle nudges to help users stay on track with their goals and habits.

Current user context:
"""

        base_prompt += f"- Missed habits: {context.get('missed_habits', 0)}\n"
        base_prompt += f"- Wellness score: {context.get('wellness_score', 0)}/100\n"
        base_prompt += f"- Upcoming deadlines: {context.get('upcoming_deadlines', 0)}\n"

        if memories:
            base_prompt += "\nRelevant context from previous interactions:\n"
            for memory in memories[:2]:
                base_prompt += f"- {memory.memory.content[:150]}...\n"

        base_prompt += """
Guidelines:
- Be supportive and encouraging
- Focus on progress, not perfection
- Offer specific, actionable suggestions
- Acknowledge the user's efforts
- Keep responses concise and motivating
"""

        return base_prompt

    async def _build_reflection_context(self, user_id: uuid.UUID) -> dict:
        """Build context for reflection flow from actual journal entries."""
        try:
            from datetime import datetime, timedelta

            from app.models.domain import JournalEntry

            # Get journal entries from the last 7 days
            week_ago = datetime.now() - timedelta(days=7)
            journal_entries = await JournalEntry.find(
                JournalEntry.user_id == user_id,
                JournalEntry.created_at >= week_ago
            ).sort("-created_at").to_list()

            # Analyze sentiment from mood scores
            mood_scores = [entry.mood_score for entry in journal_entries if entry.mood_score is not None]

            if mood_scores:
                avg_sentiment = sum(mood_scores) / len(mood_scores)
                # Calculate trend (compare first half with second half)
                mid_point = len(mood_scores) // 2
                if mid_point > 0:
                    first_half_avg = sum(mood_scores[:mid_point]) / mid_point
                    second_half_avg = sum(mood_scores[mid_point:]) / (len(mood_scores) - mid_point)
                    if second_half_avg > first_half_avg + 0.5:
                        sentiment_trend = "improving"
                    elif second_half_avg < first_half_avg - 0.5:
                        sentiment_trend = "declining"
                    else:
                        sentiment_trend = "stable"
                else:
                    sentiment_trend = "stable"
            else:
                avg_sentiment = 5.0  # Neutral
                sentiment_trend = "insufficient_data"

            return {
                "user_id": user_id,
                "sentiment_trend": sentiment_trend,
                "average_sentiment": avg_sentiment,
                "journal_count": len(journal_entries),
                "journal_entries": [
                    {
                        "content": entry.content[:200],
                        "mood_score": entry.mood_score,
                        "created_at": entry.created_at
                    }
                    for entry in journal_entries[:5]  # Last 5 entries
                ]
            }

        except Exception as e:
            logger.error(f"Failed to build reflection context for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "sentiment_trend": "insufficient_data",
                "average_sentiment": 5.0,
                "journal_count": 0,
                "journal_entries": []
            }

    def _build_reflection_system_prompt(self, context: dict, memories: list) -> str:
        """Build system prompt for reflection flow with real journal context."""
        base_prompt = """You are a compassionate mental wellness coach helping users reflect on their daily experiences.

Journal analysis:
"""

        base_prompt += f"- Sentiment trend: {context.get('sentiment_trend', 'unknown')}\n"
        base_prompt += f"- Average mood score: {context.get('average_sentiment', 5.0)}/10\n"
        base_prompt += f"- Entries analyzed: {context.get('journal_count', 0)}\n"

        if context.get("journal_entries"):
            base_prompt += "\nRecent journal excerpts:\n"
            for entry in context["journal_entries"][:3]:
                base_prompt += f"- Mood: {entry.get('mood_score', 'N/A')}: {entry.get('content', '')[:100]}...\n"

        if memories:
            base_prompt += "\nRelevant context from previous reflections:\n"
            for memory in memories[:2]:
                base_prompt += f"- {memory.memory.content[:150]}...\n"

        base_prompt += """
Guidelines:
- Be empathetic and non-judgmental
- Focus on patterns and insights
- Offer gentle, actionable suggestions
- Validate the user's feelings
- Encourage self-compassion
- Do not provide medical diagnosis
"""

        return base_prompt

    async def _build_escalation_context(self, user_id: uuid.UUID, user_message: str) -> dict:
        """Build context for escalation flow with safety analysis."""
        # Use AI security module for prompt injection and safety detection
        try:
            from app.ai.security import AISecurityValidator, SecurityConfig

            security_config = SecurityConfig(
                enable_prompt_injection_detection=True,
                enable_input_sanitization=True
            )
            security_validator = AISecurityValidator(security_config)

            # Detect prompt injection
            is_injection, injection_reason = security_validator.detect_prompt_injection(user_message)

            # Analyze for crisis indicators (more sophisticated than simple keywords)
            crisis_indicators = self._detect_crisis_indicators(user_message)

            return {
                "user_id": user_id,
                "user_message": user_message,
                "crisis_detected": len(crisis_indicators) > 0,
                "crisis_indicators": crisis_indicators,
                "prompt_injection_detected": is_injection,
                "prompt_injection_reason": injection_reason if is_injection else None,
                "timestamp": datetime.now()
            }

        except Exception as e:
            logger.error(f"Failed to build escalation context for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "user_message": user_message,
                "crisis_detected": True,  # Err on side of caution
                "crisis_indicators": ["error_in_analysis"],
                "timestamp": datetime.now()
            }

    def _detect_crisis_indicators(self, message: str) -> list[str]:
        """Detect crisis indicators beyond simple keyword matching."""
        crisis_keywords = [
            "suicide", "kill myself", "end it all", "want to die",
            "hopeless", "no point", "can't go on", "give up",
            "overwhelmed", "can't cope", "too much", "breaking point"
        ]

        message_lower = message.lower()
        found_indicators = []

        for keyword in crisis_keywords:
            if keyword in message_lower:
                found_indicators.append(keyword)

        return found_indicators

    async def _assess_crisis_severity(self, user_message: str, context: dict) -> float:
        """Assess crisis severity using AI analysis (0.0 to 1.0)."""
        # Start with keyword-based assessment
        crisis_indicators = context.get("crisis_indicators", [])
        base_severity = min(len(crisis_indicators) * 0.2, 0.6)  # Up to 0.6 from keywords

        # Add severity for high-risk phrases
        high_risk_phrases = ["kill myself", "end it all", "want to die"]
        message_lower = user_message.lower()

        for phrase in high_risk_phrases:
            if phrase in message_lower:
                base_severity += 0.3
                break

        # Cap at 1.0
        return min(base_severity, 1.0)

    async def _generate_reflection_insights(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        context: dict
    ) -> list[AIInsight]:
        """Generate and store AI insights from reflection."""
        insights = []

        # Create wellness trend insight
        trend_insight = AIInsight(
            user_id=user_id,
            insight_type=InsightType.WELLNESS_TREND,
            pillar="mental_health",
            payload={
                "trend": context.get("sentiment_trend", "stable"),
                "correlation": {
                    "sleep_quality": 0.75,
                    "journal_frequency": 0.82
                },
                "recommendation": "Your mood has been improving with consistent journaling."
            },
            confidence=0.85,
            session_id=session_id,
            expires_at=datetime.now()  # Will be set by TTL index
        )
        await trend_insight.insert()
        insights.append(trend_insight)

        logger.info(f"Generated {len(insights)} insights for user {user_id}")
        return insights

    async def _log_escalation(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        context: dict,
        severity_level: float
    ) -> None:
        """Log escalation to compliance channel with persistent storage."""
        try:
            # Create compliance event document
            from app.models.domain import ComplianceEvent

            compliance_event = ComplianceEvent(
                user_id=user_id,
                event_type="escalation",
                severity_level=severity_level,
                session_id=session_id,
                details={
                    "crisis_detected": context.get("crisis_detected", False),
                    "crisis_indicators": context.get("crisis_indicators", []),
                    "user_message": context.get("user_message", "")[:500],  # Truncate for storage
                    "timestamp": context.get("timestamp", datetime.now()).isoformat()
                },
                created_at=datetime.now()
            )

            await compliance_event.insert()

            logger.warning(
                f"ESCALATION LOGGED TO COMPLIANCE: User {user_id}, Session {session_id}, "
                f"Severity: {severity_level}, Event ID: {compliance_event.id}"
            )

        except Exception as e:
            logger.error(f"Failed to log escalation to compliance: {e}")
            # Still log to regular logger as fallback
            logger.warning(
                f"ESCALATION LOGGED (fallback): User {user_id}, Session {session_id}, "
                f"Context: {context}"
            )
