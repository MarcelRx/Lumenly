# Lumenly AI Architecture

## Overview

Lumenly's AI architecture is designed around a multi-agent system with memory management, knowledge retrieval, and secure tool execution. The architecture prioritizes privacy, tenant isolation, and security while enabling personalized coaching experiences.

## AI Components and Responsibilities

### RAG Orchestrator

**Location:** `apps/backend/app/ai/rag/orchestrator.py`

**Responsibilities:**
- Unified retrieval-augmented generation pipeline
- Security validation (prompt injection, input sanitization, output filtering)
- Memory retrieval coordination (short-term and long-term)
- Knowledge retrieval coordination
- Context construction and ranking
- LLM generation orchestration
- Response validation

**Inputs:**
- user_id: str (for tenant isolation)
- query: str (user's query)
- enable_memory: bool (whether to retrieve memory context)
- enable_knowledge: bool (whether to retrieve knowledge context)

**Outputs:**
- RAGResponse with:
  - content: str (generated response)
  - context_used: dict (counts of context items used)
  - retrieval_stats: dict (total context items)
  - security_validation: dict (validation results)
  - metadata: dict (model, usage)

**Dependencies:**
- LLMProviderInterface (for generation)
- EmbeddingProviderInterface (for query embedding)
- MemoryManager (for context retrieval)
- KnowledgeRetriever (optional, for knowledge retrieval)
- AISecurityValidator (for security validation)

**Failure Behavior:**
- Logs errors with full context
- Raises exception on failure
- No automatic fallback (caller must handle)

**Evidence:**
- Implementation in `apps/backend/app/ai/rag/orchestrator.py`
- Tests in `test_rag_orchestrator.py`

### Memory Engine

#### Memory Manager

**Location:** `apps/backend/app/ai/memory_engine/manager.py`

**Responsibilities:**
- Orchestrate short-term and long-term memory
- Build context for AI generation
- Save conversation turns

**Inputs:**
- user_id: str
- current_query: str
- query_vector: Optional[list[float]]

**Outputs:**
- dict with system_prompt and chat_history

**Dependencies:**
- ShortTermMemory (Redis-based)
- LongTermMemory (Qdrant-based)

**Failure Behavior:**
- Returns empty context on error
- Logs error message

**Evidence:**
- Implementation in `apps/backend/app/ai/memory_engine/manager.py`
- Tests in `test_memory_manager.py`

#### Short-Term Memory

**Location:** `apps/backend/app/ai/memory_engine/short_term.py`

**Responsibilities:**
- Store conversation history in Redis
- Retrieve recent conversation history
- Support per-user isolation

**Inputs:**
- user_id: str
- role: str (user, assistant)
- content: str

**Outputs:**
- List of conversation messages (role, content)

**Dependencies:**
- Redis client

**Failure Behavior:**
- Redis errors logged and raised

**Evidence:**
- Implementation in `apps/backend/app/ai/memory_engine/short_term.py`
- Tests in `test_memory_integration.py`

#### Long-Term Memory

**Location:** `apps/backend/app/ai/memory_engine/long_term.py`

**Responsibilities:**
- Store memories as vectors in Qdrant
- Retrieve relevant memories via semantic search
- Support per-user isolation

**Inputs:**
- user_id: str
- content: str
- query_vector: list[float]
- top_k: int

**Outputs:**
- List of relevant memory strings

**Dependencies:**
- Qdrant client
- EmbeddingProviderInterface

**Failure Behavior:**
- Qdrant errors logged and raised

**Evidence:**
- Implementation in `apps/backend/app/ai/memory_engine/long_term.py`
- Tests in `test_memory_integration.py`

### Agent System

#### Base Agent

**Location:** `apps/backend/app/ai/agents/base.py`

**Responsibilities:**
- Define contract for all specialized agents
- Provide tool registration mechanism
- Build LLM messages with context
- Execute registered tools

**Inputs:**
- query: str
- AgentContext (user_id, conversation_history, retrieved_memories, knowledge_context, user_preferences, current_state)

**Outputs:**
- AgentResponse (content, agent_type, confidence, tool_calls, metadata, follow_up_questions)

**Dependencies:**
- LLMProviderInterface

**Failure Behavior:**
- Abstract class, no implementation

**Evidence:**
- Implementation in `apps/backend/app/ai/agents/base.py`
- No concrete implementations exist

#### Agent Router

**Location:** `apps/backend/app/ai/agent_system/router.py`

**Responsibilities:**
- Route queries to appropriate agent type using keyword matching
- Support 8 agent types: LIFE_STRATEGIST, MENTAL_WELLNESS, HABIT_COACH, LEARNING_COACH, FITNESS_COACH, CAREER_COACH, FINANCIAL_COACH, RELATIONSHIP_COACH

**Inputs:**
- query: str
- chat_history: Optional[list[dict]]

**Outputs:**
- AgentType enum value

**Dependencies:**
- None (stateless)

**Failure Behavior:**
- Defaults to LIFE_STRATEGIST if no keywords match

**Evidence:**
- Implementation in `apps/backend/app/ai/agent_system/router.py`
- Tests in test suite

#### AI Orchestrator

**Location:** `apps/backend/app/ai/orchestration/router.py`

**Responsibilities:**
- Central orchestration for AI request processing
- Route requests to appropriate agents
- Coordinate memory retrieval
- Handle tool execution
- Save conversation turns

**Inputs:**
- query: str
- user_id: str
- conversation_history: Optional[List[Dict[str, str]]]
- enable_memory: bool

**Outputs:**
- AgentResponse

**Dependencies:**
- LLMProviderInterface
- EmbeddingProviderInterface (optional)
- MemoryManager (optional)
- Registered agents

**Failure Behavior:**
- Returns safe fallback response if enable_fallback=True
- Raises exception if enable_fallback=False

**Evidence:**
- Implementation in `apps/backend/app/ai/orchestration/router.py`
- No tests for orchestrator specifically

### Knowledge Brain

#### Knowledge Retriever

**Location:** `apps/backend/app/ai/knowledge_brain/retriever.py`

**Responsibilities:**
- Search knowledge base for relevant chunks
- Enforce tenant isolation with user_id filter
- Format search results

**Inputs:**
- user_id: str
- query: str
- top_k: int

**Outputs:**
- List of dicts with document_title, chunk_text, score

**Dependencies:**
- Qdrant client
- Embedding function

**Failure Behavior:**
- Qdrant errors raised

**Evidence:**
- Implementation in `apps/backend/app/ai/knowledge_brain/retriever.py`
- Tests in test suite

#### Document Chunker

**Location:** `apps/backend/app/ai/knowledge_brain/chunker.py`

**Responsibilities:**
- Chunk documents into smaller segments
- Support configurable chunk size and overlap

**Inputs:**
- text: str
- chunk_size: int
- chunk_overlap: int

**Outputs:**
- List of text chunks

**Dependencies:**
- None

**Failure Behavior:**
- Empty list on empty input

**Evidence:**
- Implementation in `apps/backend/app/ai/knowledge_brain/chunker.py`

#### Document Ingestor

**Location:** `apps/backend/app/ai/knowledge_brain/ingestor.py`

**Responsibilities:**
- Orchestrate document ingestion pipeline
- Coordinate chunking, embedding, and storage

**Inputs:**
- document_text: str
- user_id: str
- embedding_provider: EmbeddingProviderInterface

**Outputs:**
- List of vector IDs

**Dependencies:**
- Chunker
- EmbeddingProviderInterface
- Qdrant client

**Failure Behavior:**
- Errors logged and raised

**Evidence:**
- Implementation in `apps/backend/app/ai/knowledge_brain/ingestor.py`

### Tool Registry

**Location:** `apps/backend/app/ai/tools/registry.py`

**Responsibilities:**
- Register allowed tools with validation
- Validate tool arguments against schemas
- Check tool authorization
- Execute tools with tenant isolation
- Log security events

**Inputs:**
- tool_name: str
- arguments: Dict[str, Any]
- user_id: uuid.UUID
- user_role: str

**Outputs:**
- Tool execution result (dict)

**Dependencies:**
- MongoDB (for tool executors that access database)
- Prometheus metrics (for security event tracking)

**Failure Behavior:**
- ValueError for unregistered tools or invalid arguments
- PermissionError for authorization failures
- Generic error for execution failures

**Evidence:**
- Implementation in `apps/backend/app/ai/tools/registry.py`
- Three registered tools: check_habit_status, get_goal_progress, get_recent_journals
- Tests in `test_tool_registry_security.py` and `test_tool_security_tenant_isolation.py`

### LLM Interface

**Location:** `apps/backend/app/ai/llm/`

**Responsibilities:**
- Abstract interface for LLM providers
- Provider implementations (Groq, Gemini, Mock)
- LLM usage metrics

**Inputs:**
- messages: List[LLMMessage]
- Optional: temperature, max_tokens, etc.

**Outputs:**
- LLMResponse with content, model, usage

**Dependencies:**
- Provider-specific APIs (Groq, Gemini)

**Failure Behavior:**
- Provider-specific error handling
- Mock provider always succeeds

**Evidence:**
- Interface in `apps/backend/app/ai/llm/interface.py`
- Providers in `apps/backend/app/ai/llm/providers.py` and `providers_gemini.py`
- Tests in `test_ai_llm_interface.py`

### Embedding Interface

**Location:** `apps/backend/app/ai/embeddings/`

**Responsibilities:**
- Abstract interface for embedding providers
- Provider implementations (OpenAI, Cohere, FastEmbed, Sentence Transformers, Mock)

**Inputs:**
- text: str

**Outputs:**
- List[float] (embedding vector)

**Dependencies:**
- Provider-specific APIs

**Failure Behavior:**
- Provider-specific error handling
- Mock provider returns fixed vector

**Evidence:**
- Interface in `apps/backend/app/ai/embeddings/interface.py`
- Providers in `apps/backend/app/ai/embeddings/providers.py`
- Tests in test suite

### AI Security

**Location:** `apps/backend/app/ai/security.py`

**Responsibilities:**
- Prompt injection detection
- Input sanitization
- Output filtering
- User access validation
- Tenant isolation enforcement

**Inputs:**
- text: str (for detection/sanitization/filtering)
- user_id: str (for access validation)

**Outputs:**
- bool (for detection)
- str (for sanitization/filtering)
- bool (for access validation)

**Dependencies:**
- None (rule-based)

**Failure Behavior:**
- Returns safe defaults on error

**Evidence:**
- Implementation in `apps/backend/app/ai/security.py`
- Tests in security test suite

## Model Providers and Integrations

### LLM Providers

**Groq (Primary)**
- Model: llama-3.3-70b-versatile
- Used for: Primary generation, voice-fast paths
- Configuration: GROQ_API_KEY
- Evidence: Provider implementation in `apps/backend/app/ai/llm/providers.py`

**Gemini (Fallback/Enterprise)**
- Model: gemini-2.5-flash (configurable via GEMINI_MODEL)
- Used for: Fallback, enterprise tier, higher fidelity
- Configuration: GEMINI_API_KEY, GEMINI_MODEL, GEMINI_API_VERSION
- Evidence: Provider implementation in `apps/backend/app/ai/llm/providers_gemini.py`

**Mock (Test)**
- Model: mock-model
- Used for: Test environment, development without API keys
- Configuration: No API key required
- Evidence: Provider implementation in `apps/backend/app/ai/llm/providers.py`

### Embedding Providers

**OpenAI**
- Model: text-embedding-3-small
- Dimensions: 1536
- Configuration: OPENAI_API_KEY
- Evidence: Provider implementation in `apps/backend/app/ai/embeddings/providers.py`

**Cohere**
- Model: embed-english-v3.0
- Dimensions: 1024
- Configuration: COHERE_API_KEY
- Evidence: Provider implementation in `apps/backend/app/ai/embeddings/providers.py`

**FastEmbed**
- Model: BAAI/bge-small-en-v1.5
- Dimensions: 384
- Configuration: No API key required
- Evidence: Provider implementation in `apps/backend/app/ai/embeddings/providers.py`

**Sentence Transformers**
- Model: all-MiniLM-L6-v2
- Dimensions: 384
- Configuration: No API key required
- Evidence: Provider implementation in `apps/backend/app/ai/embeddings/providers.py`

**Mock (Test)**
- Model: mock-model
- Dimensions: Configurable (matches VECTOR_DIMENSION setting)
- Configuration: No API key required
- Evidence: Provider implementation in `apps/backend/app/ai/embeddings/providers.py`

## Model Selection and Configuration

**Selection Logic (in `apps/backend/app/api/deps.py`):**

1. **Test Environment:** Always use mock provider
2. **Production Environment:**
   - Use Groq if GROQ_API_KEY is valid (30+ chars, not placeholder)
   - Use Gemini if GEMINI_API_KEY is valid (30+ chars, not placeholder)
   - Fail if neither is valid (no mock in production)
3. **Development/Staging:**
   - Default to mock
   - Use Gemini if GEMINI_API_KEY is valid (30+ chars, not placeholder)
   - Use Groq if GROQ_API_KEY is valid (30+ chars, not placeholder)

**Configuration Validation:**
- Embedding provider must match VECTOR_DIMENSION setting
- Validated at startup in production/staging
- Raises ValueError on mismatch

**Evidence:**
- Provider selection logic in `apps/backend/app/api/deps.py`
- Configuration validation in `apps/backend/app/core/config.py`

## Prompt and Context Construction

**System Prompt Construction (in RAG Orchestrator):**
1. Base prompt: "You are a helpful AI assistant for Lumenly."
2. Add long-term memories if available
3. Add knowledge context if available
4. Customized per request

**Message Construction:**
1. System message with constructed prompt
2. Last 10 conversation turns from short-term memory
3. Current user query

**Context Assembly:**
- Short-term memory: Last N messages from Redis
- Long-term memory: Top-k semantic matches from Qdrant
- Knowledge context: Top-k document chunks from Qdrant
- Fusion: Ranked and combined based on relevance

**Evidence:**
- Prompt construction in `apps/backend/app/ai/rag/orchestrator.py`
- Message construction in `apps/backend/app/ai/rag/orchestrator.py`
- Context building in `apps/backend/app/ai/memory_engine/manager.py`

## Tool Access and Execution Boundaries

**Tool Registration:**
- Only registered tools can be executed
- Tools registered in ToolRegistry constructor
- Each tool has schema, authorization, and executor

**Tool Authorization:**
- require_user_context: Tool must have user_id
- allowed_roles: Specific roles required (optional)
- require_tenant_isolation: Tool must enforce user_id filtering
- max_arg_size: Maximum argument size validation

**Tool Execution:**
1. Check tool is registered
2. Validate arguments against schema
3. Check authorization
4. Execute with user context
5. Enforce tenant isolation at database level
6. Log security events on cross-tenant attempts

**Security Boundaries:**
- User_id filtering in all database queries
- Generic error messages to prevent enumeration
- Security event logging for compliance
- Prometheus metrics for security events

**Evidence:**
- Tool registry in `apps/backend/app/ai/tools/registry.py`
- Tool executors with database access
- Security tests in `test_tool_registry_security.py`

## Memory and Retrieval Architecture

**Short-Term Memory:**
- Storage: Redis lists
- Key pattern: `short_term_memory:{user_id}`
- TTL: Not configured (indefinite retention)
- Retrieval: Last N messages
- Isolation: Per-user keys

**Long-Term Memory:**
- Storage: Qdrant vectors
- Collection: Per-user collections or user_id filter
- Metadata: user_id, timestamp, content
- Retrieval: Semantic search with top-k
- Isolation: user_id filter in Qdrant queries

**Memory Consolidation:**
- Framework exists in `apps/backend/app/ai/memory/consolidation.py`
- Not actively used in current implementation

**Memory Forgetting:**
- Framework exists in `apps/backend/app/ai/memory/forgetting.py`
- Not actively used in current implementation

**Evidence:**
- Short-term memory in `apps/backend/app/ai/memory_engine/short_term.py`
- Long-term memory in `apps/backend/app/ai/memory_engine/long_term.py`
- Memory manager in `apps/backend/app/ai/memory_engine/manager.py`

## Structured Output Validation

**Current State:**
- Limited structured output validation
- Pydantic schemas for request/response validation
- Tool argument validation against JSON schemas
- No LLM response structure validation beyond basic filtering

**Evidence:**
- Pydantic schemas in `apps/backend/app/schemas/`
- Tool argument validation in `apps/backend/app/ai/tools/registry.py`

## Evaluation Mechanisms

**Current State:**
- No automated evaluation framework
- Manual testing through test suite
- No human evaluation metrics
- No A/B testing infrastructure

**Evidence:**
- Test suite with 832 tests
- No evaluation framework code found

## Model Failure Handling and Fallback Behavior

**LLM Provider Failures:**
- Provider-specific error handling
- No automatic fallback between providers
- Orchestrator has enable_fallback flag for safe responses
- Fallback response: "I apologize, but I encountered an error processing your request. Please try again."

**Embedding Provider Failures:**
- Provider-specific error handling
- No automatic fallback between providers
- Errors propagate to caller

**Redis Failures:**
- Rate limiting: Fail-closed by default (configurable)
- Short-term memory: Errors logged and raised
- Caching: Errors logged and raised

**Qdrant Failures:**
- Long-term memory: Errors logged and raised
- Knowledge retrieval: Errors logged and raised
- No fallback to other storage

**Evidence:**
- Error handling in respective provider implementations
- Rate limiting configuration in `apps/backend/app/core/config.py`

## Security and Privacy Boundaries for AI Processing

**Tenant Isolation:**
- User_id filtering in all database queries
- User_id filtering in all Qdrant searches
- Tool execution enforces ownership at database level
- Cross-tenant attempts logged as security events

**Prompt Injection Detection:**
- Regex-based detection
- Keyword-based detection
- No ML-based detection
- Logs detected attempts

**Input Sanitization:**
- Removes potentially malicious patterns
- Sanitizes before LLM processing
- Logs sanitization events

**Output Filtering:**
- Removes sensitive content patterns
- Filters after LLM generation
- Logs filtering events

**Data Minimization:**
- Only necessary context passed to LLM
- No PII in system prompts
- User IDs used only for isolation

**Evidence:**
- AI security in `apps/backend/app/ai/security.py`
- Tool registry security in `apps/backend/app/ai/tools/registry.py`
- Security tests in test suite

## Distinguishing AI Components from Application Services

**AI Components (in `apps/backend/app/ai/`):**
- RAG Orchestrator: Unified AI pipeline
- Memory Engine: AI context management
- Agent System: Multi-agent framework
- Knowledge Brain: Document-based context
- LLM Interface: Model abstraction
- Embedding Interface: Vector generation
- Tool Registry: AI tool execution
- AI Security: AI-specific security

**Application Services (in `apps/backend/app/services/`):**
- Coaching Flow: Business logic for coaching sessions
- LLM Service: Service layer for LLM operations
- Vector Service: Service layer for vector operations

**Key Difference:**
- AI components focus on model interactions, context building, and AI-specific logic
- Application services focus on business logic, workflows, and domain operations

**Evidence:**
- AI components in `apps/backend/app/ai/`
- Application services in `apps/backend/app/services/`
