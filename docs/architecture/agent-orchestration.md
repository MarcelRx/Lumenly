# Agent Responsibilities and Orchestration

## Overview

Lumenly's agent system is designed to support multiple specialized AI coaches for different life domains. Currently, only the agent framework exists; concrete agent implementations are not yet implemented. This document describes the framework, the intended agent types, and how agents would be orchestrated once implemented.

## Confirmed Agent Components

### Base Agent (Framework Only)

**Name:** BaseAgent
**Implementation Location:** `apps/backend/app/ai/agents/base.py`
**Purpose:** Abstract base class defining the contract for all specialized agents
**Status:** Framework implemented, no concrete implementations

**Responsibilities:**
- Define standard interface for all agents
- Provide tool registration mechanism
- Build LLM messages with context
- Execute registered tools
- Return standardized AgentResponse

**Explicit Non-Responsibilities:**
- Does not implement domain-specific logic
- Does not provide routing logic (handled by AgentRouter)
- Does not handle memory retrieval (handled by MemoryManager)

**Inputs:**
- query: str (user's query)
- context: AgentContext with:
  - user_id: str
  - conversation_history: List[Dict[str, str]]
  - retrieved_memories: List[str]
  - knowledge_context: Optional[str]
  - user_preferences: Optional[Dict[str, Any]]
  - current_state: Optional[Dict[str, Any]]

**Outputs:**
- AgentResponse with:
  - content: str (generated response)
  - agent_type: str (agent identifier)
  - confidence: float (response confidence)
  - tool_calls: Optional[List[Dict[str, Any]]]
  - metadata: Optional[Dict[str, Any]]
  - follow_up_questions: Optional[List[str]]

**Preconditions:**
- LLM provider must be initialized
- Agent must be registered with AgentFactory
- Context must contain valid user_id

**Postconditions:**
- Returns valid AgentResponse
- Tool calls executed successfully (if any)
- Conversation turn saved to memory (if enabled)

**Dependencies:**
- LLMProviderInterface (for generation)
- Registered tools (optional)

**Permitted Tools:**
- Any tool registered via `register_tool()` method
- Tools must be callable with appropriate signature

**Invocation and Execution Mechanism:**
- Instantiated via AgentFactory.create()
- Process method called with query and context
- Abstract `process()` method must be implemented by subclasses

**Communication with Other Components:**
- Receives context from orchestrator
- Uses LLM provider for generation
- Executes tools via tool registry
- Returns response to orchestrator

**State Management and Persistence:**
- Stateless by design
- No persistent state maintained
- State passed via AgentContext

**Authentication and Authorization Context:**
- User_id from context used for tenant isolation
- Tool execution enforces ownership at database level
- No agent-specific authorization beyond user context

**Timeouts, Retries, and Idempotency Behavior:**
- No built-in timeout handling
- No built-in retry logic
- Not designed for idempotency (stateful conversations)

**Failure Modes and Recovery Behavior:**
- Abstract class, no implementation
- Subclasses must define failure behavior
- Orchestrator may provide fallback responses

**Logging and Observability:**
- No built-in logging in base class
- Subclasses should implement logging
- Tool execution logged in tool registry

**Tests and Verification Evidence:**
- No tests for BaseAgent (abstract class)
- Framework verified through usage in other components

**Known Limitations:**
- No concrete implementations exist
- No domain-specific logic implemented
- No tool calling examples

### Agent Router

**Name:** AgentRouter
**Implementation Location:** `apps/backend/app/ai/agent_system/router.py`
**Purpose:** Route user queries to appropriate specialized agent using keyword matching
**Status:** Implemented

**Responsibilities:**
- Match queries to agent types using keywords
- Provide default fallback (LIFE_STRATEGIST)
- Support 8 agent types

**Explicit Non-Responsibilities:**
- Does not execute agents (only routes)
- Does not handle memory retrieval
- Does not provide ML-based routing

**Inputs:**
- query: str (user's query)
- chat_history: Optional[list[dict]] (for context, not currently used)

**Outputs:**
- AgentType enum value (one of 8 types)

**Preconditions:**
- None (stateless)

**Postconditions:**
- Returns valid AgentType enum value

**Dependencies:**
- None (stateless)

**Permitted Tools:**
- None (routing only)

**Invocation and Execution Mechanism:**
- Instantiated via dependency injection
- route_query() method called with query

**Communication with Other Components:**
- Receives queries from orchestrator or coaching service
- Returns AgentType to caller
- Caller instantiates appropriate agent

**State Management and Persistence:**
- Stateless
- Keyword mappings stored in instance variable

**Authentication and Authorization Context:**
- None (routing only)

**Timeouts, Retries, and Idempotency Behavior:**
- N/A (stateless, synchronous)

**Failure Modes and Recovery Behavior:**
- Always returns a value (no failure mode)
- Defaults to LIFE_STRATEGIST if no keywords match

**Logging and Observability:**
- Logs routing decisions with debug level
- Logs score for each agent type

**Tests and Verification Evidence:**
- Tests in coaching integration tests
- Keyword mappings verified in implementation

**Known Limitations:**
- Keyword-based routing (not ML-based)
- Does not use chat history for context
- No confidence thresholding

### AI Orchestrator

**Name:** AIOrchestrator
**Implementation Location:** `apps/backend/app/ai/orchestration/router.py`
**Purpose:** Central orchestration for AI request processing
**Status:** Implemented

**Responsibilities:**
- Route requests to appropriate agents
- Coordinate memory retrieval
- Handle tool execution
- Save conversation turns
- Provide fallback responses

**Explicit Non-Responsibilities:**
- Does not implement agent logic
- Does not implement memory storage (delegates to MemoryManager)
- Does not implement LLM generation (delegates to LLMProvider)

**Inputs:**
- query: str (user's query)
- user_id: str (user identifier)
- conversation_history: Optional[List[Dict[str, str]]]
- enable_memory: bool (whether to use memory)

**Outputs:**
- AgentResponse

**Preconditions:**
- At least one agent must be registered
- LLM provider must be initialized
- Memory manager must be initialized (if enable_memory=True)

**Postconditions:**
- Returns valid AgentResponse
- Conversation turn saved to memory (if enable_memory=True)

**Dependencies:**
- LLMProviderInterface
- EmbeddingProviderInterface (optional)
- MemoryManager (optional)
- Registered agents

**Permitted Tools:**
- Delegates to agent implementations

**Invocation and Execution Mechanism:**
- Instantiated with dependencies
- process_request() method called with query and user_id
- Internal pipeline: route → retrieve context → process → save

**Communication with Other Components:**
- Uses AgentRouter for routing
- Uses MemoryManager for context
- Uses LLMProvider for generation
- Calls agent.process() for agent-specific logic

**State Management and Persistence:**
- Stateless (per-request)
- Agent registry stored in instance variable

**Authentication and Authorization Context:**
- User_id passed to agents and memory manager
- Tenant isolation enforced by dependencies

**Timeouts, Retries, and Idempotency Behavior:**
- No built-in timeout handling
- No built-in retry logic
- Not idempotent (stateful conversations)

**Failure Modes and Recovery Behavior:**
- If enable_fallback=True: returns safe fallback response
- If enable_fallback=False: raises exception
- Logs errors with full context

**Logging and Observability:**
- Logs routing decisions
- Logs memory retrieval failures
- Logs processing failures

**Tests and Verification Evidence:**
- No specific tests for AIOrchestrator
- Used in coaching service

**Known Limitations:**
- No concrete agents registered
- No parallel agent execution
- No agent fusion

## Intended Agent Types (Not Yet Implemented)

The following agent types are defined in the AgentType enum but have no concrete implementations:

### Life Strategist

**AgentType:** LIFE_STRATEGIST
**Intended Responsibility:** Long-term planning, habit formation, weekly reviews
**Intended Data Sources:** goals, journal_entries, profiles
**Status:** Not implemented

### Mental Wellness Coach

**AgentType:** MENTAL_WELLNESS
**Intended Responsibility:** Mood detection, crisis escalation, reflection exercises
**Intended Data Sources:** profiles.wellnessScore, recent messages
**Status:** Not implemented

### Habit Coach

**AgentType:** HABIT_COACH
**Intended Responsibility:** Habit creation, streaks, behavioral change
**Intended Data Sources:** habits, profiles
**Status:** Not implemented

### Learning Coach

**AgentType:** LEARNING_COACH
**Intended Responsibility:** Skill recommendation, spaced repetition, study plans
**Intended Data Sources:** documents, memory_links
**Status:** Not implemented

### Fitness Coach

**AgentType:** FITNESS_COACH
**Intended Responsibility:** Exercise plans, biometrics integration
**Intended Data Sources:** profiles, external health APIs
**Status:** Not implemented

### Career Coach

**AgentType:** CAREER_COACH
**Intended Responsibility:** Job market insights, resume optimization, skill gaps
**Intended Data Sources:** documents, external labor-market feeds
**Status:** Not implemented

### Financial Coach

**AgentType:** FINANCIAL_COACH
**Intended Responsibility:** Budgeting, spending awareness, saving goals
**Intended Data Sources:** goals, profiles, external market data
**Status:** Not implemented

### Relationship Coach

**AgentType:** RELATIONSHIP_COACH
**Intended Responsibility:** Communication coaching, conflict resolution
**Intended Data Sources:** Conversation snippets, sentiment trends
**Status:** Not implemented

## Agent Component Summary Table

| Component | Responsibility | Inputs | Outputs | Dependencies | Failure Behavior | Evidence |
|-----------|---------------|--------|---------|--------------|------------------|----------|
| BaseAgent | Agent framework | query, AgentContext | AgentResponse | LLMProviderInterface | N/A (abstract) | base.py |
| AgentRouter | Query routing | query, chat_history | AgentType | None | Default to LIFE_STRATEGIST | router.py |
| AIOrchestrator | Request orchestration | query, user_id, history | AgentResponse | LLMProvider, MemoryManager, Agents | Fallback response or exception | orchestration/router.py |
| Life Strategist | Long-term planning | query, context | AgentResponse | (not implemented) | (not implemented) | Not implemented |
| Mental Wellness Coach | Mood/crisis support | query, context | AgentResponse | (not implemented) | (not implemented) | Not implemented |
| Habit Coach | Habit management | query, context | AgentResponse | (not implemented) | (not implemented) | Not implemented |
| Learning Coach | Skill development | query, context | AgentResponse | (not implemented) | (not implemented) | Not implemented |
| Fitness Coach | Exercise planning | query, context | AgentResponse | (not implemented) | (not implemented) | Not implemented |
| Career Coach | Career guidance | query, context | AgentResponse | (not implemented) | (not implemented) | Not implemented |
| Financial Coach | Financial planning | query, context | AgentResponse | (not implemented) | (not implemented) | Not implemented |
| Relationship Coach | Relationship coaching | query, context | AgentResponse | (not implemented) | (not implemented) | Not implemented |

## Agent Orchestration Flow (When Implemented)

**Current State (Framework Only):**
1. Query received by orchestrator
2. AgentRouter routes to agent type (keyword-based)
3. Orchestrator retrieves context from memory
4. Orchestrator calls agent.process() (would fail - no agents)
5. Orchestrator saves conversation turn
6. Response returned

**Intended State (With Concrete Agents):**
1. Query received by orchestrator
2. AgentRouter routes to agent type (keyword-based, could be ML-based)
3. Orchestrator retrieves context from memory
4. Agent processes query with context
5. Agent may execute tools via tool registry
6. Agent returns response
7. Orchestrator saves conversation turn
8. Response returned

**Parallel Execution (Planned):**
- Multiple agents could be invoked in parallel
- Fusion engine would merge responses
- Priority matrix would resolve conflicts
- Synthesizer would build final response

## Communication and Coordination

**Current Communication:**
- Orchestrator → AgentRouter: routing decision
- Orchestrator → MemoryManager: context retrieval
- Orchestrator → Agent: process request (would fail)
- Agent → Tool Registry: tool execution (would fail)
- Orchestrator → MemoryManager: save turn

**Intended Communication:**
- Orchestrator → Multiple Agents: parallel processing
- Agents → Fusion Engine: response merging
- Fusion Engine → Synthesizer: final response
- All components → Logging: observability

## State Management

**Current State:**
- Agents are stateless
- State passed via AgentContext
- Conversation history in short-term memory
- Long-term memories in Qdrant

**Intended State:**
- Agents remain stateless
- Session state in short-term memory
- User state in profiles (MongoDB)
- Persistent patterns in long-term memory

## Known Limitations

1. **No Concrete Agents:** Only framework exists; 8 agent types defined but not implemented
2. **Keyword-Based Routing:** Simple keyword matching, not ML-based
3. **No Parallel Execution:** Agents cannot be invoked in parallel
4. **No Fusion Engine:** No mechanism to merge multiple agent responses
5. **No Agent Tool Calling:** Framework exists but no agents use tools
6. **No Agent Collaboration:** No mechanism for agents to collaborate or share information
7. **No Agent Learning:** No mechanism for agents to learn from interactions

## Future Improvements

1. **Implement Concrete Agents:** Create actual implementations for all 8 agent types
2. **ML-Based Routing:** Use intent classification for better routing
3. **Parallel Execution:** Support invoking multiple agents in parallel
4. **Fusion Engine:** Implement response merging and conflict resolution
5. **Agent Tool Calling:** Enable agents to use tools via tool registry
6. **Agent Collaboration:** Enable agents to share information and collaborate
7. **Agent Learning:** Implement feedback loops for agent improvement
