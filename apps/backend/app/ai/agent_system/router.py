# apps/backend/app/ai/agent_system/router.py
import logging
from typing import Optional

from app.ai.agent_system.schemas.agent_types import AgentType

logger = logging.getLogger(__name__)


class AgentRouter:
    """Routes user queries to the appropriate specialized AI coach agent."""

    def __init__(self):
        """Initialize the agent router with keyword mappings."""
        self._keyword_mappings = {
            AgentType.FITNESS_COACH: [
                "workout",
                "gym",
                "exercise",
                "fitness",
                "run",
                "running",
                "lift",
                "training",
                "cardio",
                "strength",
                "muscle",
                "weight",
                "sport",
                "athlete",
                "physical",
                "health",
                "yoga",
                "pilates",
                "swim",
                "cycling",
                "bike",
                "hike",
                "hiking",
                "marathon",
                "sprint",
            ],
            AgentType.HABIT_COACH: [
                "habit",
                "streak",
                "daily",
                "consistency",
                "practice",
                "build habit",
                "break habit",
                "change behavior",
                "tiny habit",
                "trigger",
                "reminder",
                "schedule",
                "morning routine",
                "evening routine",
                "ritual",
                "pattern",
                "automate",
                "willpower",
                "discipline",
                "commitment",
            ],
            AgentType.MENTAL_WELLNESS: [
                "feel",
                "anxious",
                "sad",
                "depressed",
                "stress",
                "overwhelmed",
                "anxiety",
                "mood",
                "emotion",
                "mental health",
                "therapy",
                "counseling",
                "worried",
                "fear",
                "panic",
                "lonely",
                "isolated",
                "burnout",
                "exhausted",
                "tired",
                "cope",
                "mindful",
                "meditation",
            ],
            AgentType.LEARNING_COACH: [
                "learn",
                "study",
                "memorize",
                "remember",
                "education",
                "course",
                "skill",
                "knowledge",
                "read",
                "book",
                "tutorial",
                "class",
                "exam",
                "test",
                "grade",
                "academic",
                "school",
                "university",
                "research",
                "understand",
                "comprehend",
                "practice",
                "review",
            ],
            AgentType.CAREER_COACH: [
                "career",
                "job",
                "work",
                "professional",
                "resume",
                "interview",
                "promotion",
                "salary",
                "negotiate",
                "boss",
                "colleague",
                "team",
                "productivity",
                "meeting",
                "project",
                "deadline",
                "office",
                "remote",
                "freelance",
                "startup",
                "business",
                "leadership",
                "management",
                "skill",
                "growth",
                "networking",
            ],
            AgentType.FINANCIAL_COACH: [
                "money",
                "budget",
                "spend",
                "save",
                "invest",
                "debt",
                "loan",
                "financial",
                "expense",
                "income",
                "salary",
                "cost",
                "price",
                "cheap",
                "expensive",
                "afford",
                "bank",
                "credit",
                "card",
                "investment",
                "retirement",
                "fund",
                "emergency",
                "savings",
            ],
            AgentType.RELATIONSHIP_COACH: [
                "relationship",
                "friend",
                "partner",
                "spouse",
                "boyfriend",
                "girlfriend",
                "husband",
                "wife",
                "family",
                "parent",
                "child",
                "sibling",
                "communication",
                "talk",
                "argue",
                "conflict",
                "boundary",
                "trust",
                "intimacy",
                "dating",
                "breakup",
                "divorce",
                "social",
                "connect",
                "lonely",
                "support",
            ],
        }

    def route_query(self, query: str, chat_history: Optional[list[dict]] = None) -> AgentType:
        """
        Route a user query to the appropriate agent type using keyword matching.

        Args:
            query: The user's query string
            chat_history: Optional list of previous conversation turns for context

        Returns:
            The AgentType that should handle this query
        """
        if chat_history is None:
            chat_history = []

        query_lower = query.lower()

        # Score each agent type based on keyword matches
        scores = {agent_type: 0 for agent_type in AgentType}

        for agent_type, keywords in self._keyword_mappings.items():
            for keyword in keywords:
                if keyword in query_lower:
                    scores[agent_type] += 1

        # Find the agent with the highest score
        max_score = max(scores.values())

        if max_score > 0:
            # Return the agent with the highest score
            for agent_type, score in scores.items():
                if score == max_score:
                    logger.debug(f"Routed query to {agent_type.value} (score: {score})")
                    return agent_type

        # Default to Life Strategist if no keywords match
        logger.debug("No keywords matched, defaulting to LIFE_STRATEGIST")
        return AgentType.LIFE_STRATEGIST
