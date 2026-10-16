# ADR-0003: Keyword-Based Agent Routing

## Status

Accepted (with planned migration to ML-based routing)

## Context

Lumenly is designed to support 8 specialized AI agents for different life domains:

- Life Strategist
- Mental Wellness Coach
- Habit Coach
- Learning Coach
- Fitness Coach
- Career Coach
- Financial Coach
- Relationship Coach

The system needs to route user queries to the appropriate agent. Several approaches are possible:

- Keyword-based routing (simple pattern matching)
- ML-based intent classification (more sophisticated)
- Hybrid approach (keyword-based with ML fallback)

## Decision

Lumenly currently uses keyword-based agent routing as an interim solution:

**Implementation:**

- AgentRouter in `apps/backend/app/ai/agent_system/router.py`
- Keyword mappings for each agent type
- Simple string matching on user queries
- Default fallback to LIFE_STRATEGIST if no keywords match

**Keyword Mappings:**

- LIFE_STRATEGIST: "planning", "strategy", "plan", "goal", "overall"
- MENTAL_WELLNESS: "mental", "anxiety", "depression", "stress", "mood", "feeling"
- HABIT_COACH: "habit", "routine", "daily", "consistency"
- LEARNING_COACH: "learn", "study", "skill", "knowledge", "education"
- FITNESS_COACH: "fitness", "exercise", "workout", "health", "training"
- CAREER_COACH: "career", "job", "work", "professional", "resume"
- FINANCIAL_COACH: "financial", "money", "budget", "saving", "invest"
- RELATIONSHIP_COACH: "relationship", "partner", "friend", "family", "social"

**Behavior:**

- Query is lowercased and checked against keyword lists
- Agent with highest keyword match count is selected
- If no keywords match, defaults to LIFE_STRATEGIST
- No confidence thresholding
- No use of chat history for context

**Rationale for Keyword-Based Approach:**

- Simple to implement and understand
- No ML model training required
- Predictable behavior
- Fast execution (no model inference)
- Sufficient for initial implementation
- Allows time to gather user interaction data for ML training

**Planned Migration:**

- ML-based intent classification using small LLM (Claude Haiku)
- Use of chat history for context
- Confidence thresholding
- Fallback to keyword-based routing if ML confidence is low

## Consequences

### Positive

- Simple, predictable routing behavior
- Fast execution (no model inference latency)
- No ML model training or maintenance overhead
- Easy to debug and understand
- Sufficient for initial implementation

### Negative

- Limited accuracy for complex queries
- No context from chat history
- No confidence scoring
- Hard to maintain keyword lists manually
- Limited expressiveness (cannot handle nuances)
- May misroute queries with ambiguous keywords

### Risks

- Poor user experience due to misrouted queries
- User frustration with inappropriate agent responses
- Need to manually maintain and update keyword lists
- Scalability issue as domain vocabulary grows

## Evidence

**Implementation Evidence:**

- AgentRouter in `apps/backend/app/ai/agent_system/router.py`
- AgentType enum in `apps/backend/app/ai/agent_system/schemas.py`
- Routing used in coaching service and AI orchestrator

**Test Evidence:**

- Keyword routing tested in coaching integration tests
- No dedicated agent routing test file found
- Agent routing verified through coaching integration

**Historical Context:**

- Decision made during initial agent framework implementation
- Documented as "keyword-based (not ML-based)" in architecture documentation
- Intended as interim solution before ML-based routing

**Planned Improvements:**

- ML-based routing mentioned in architecture documentation
- Intent classification using small LLM (Claude Haiku) mentioned in AI architecture documentation

## Alternatives Considered

**ML-Based Intent Classification:**

- Pros: Higher accuracy, can handle nuances, can use context
- Cons: Requires model training, higher latency, more complex, requires training data
- Status: Planned for future implementation

**Hybrid Approach (Keyword + ML):**

- Pros: Combines simplicity of keywords with accuracy of ML
- Cons: More complex, requires maintaining both systems
- Status: Possible future approach

**Rule-Based Expert System:**

- Pros: Explicit rules, predictable
- Cons: Hard to maintain, brittle, cannot handle edge cases
- Status: Not considered

**No Routing (Single Agent):**

- Pros: Simplest approach
- Cons: Defeats purpose of specialized agents
- Status: Rejected (contradicts product vision)

## References

- Agent router: `apps/backend/app/ai/agent_system/router.py`
- Agent types: `apps/backend/app/ai/agent_system/schemas.py`
- Agent orchestration: `docs/architecture/agent-orchestration.md`
- AI architecture: `docs/architecture/ai-architecture.md`
- System architecture: `docs/architecture/system-architecture.md`
