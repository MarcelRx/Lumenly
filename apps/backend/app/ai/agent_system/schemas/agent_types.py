# apps/backend/app/ai/agent_system/schemas/agent_types.py
from enum import Enum


class AgentType(str, Enum):
    """Enumeration of available AI coach agents."""
    
    LIFE_STRATEGIST = "life_strategist"
    MENTAL_WELLNESS = "mental_wellness"
    HABIT_COACH = "habit_coach"
    LEARNING_COACH = "learning_coach"
    FITNESS_COACH = "fitness_coach"
    CAREER_COACH = "career_coach"
    FINANCIAL_COACH = "financial_coach"
    RELATIONSHIP_COACH = "relationship_coach"
