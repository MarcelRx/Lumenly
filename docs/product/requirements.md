# Lumenly Product Requirements

## Functional Requirements

### Authentication and Authorization

**REQ-AUTH-001:** Users must be able to register with email and password
- Status: Implemented
- Evidence: `apps/backend/app/api/endpoints/auth.py`, test coverage in `test_auth.py`

**REQ-AUTH-002:** Users must be able to authenticate with JWT access tokens
- Status: Implemented
- Evidence: `apps/backend/app/core/security.py`, JWT token generation and validation

**REQ-AUTH-003:** Access tokens must expire after 15 minutes
- Status: Implemented
- Evidence: `ACCESS_TOKEN_EXPIRE_MINUTES = 15` in config.py

**REQ-AUTH-004:** Refresh tokens must be valid for 7 days
- Status: Implemented
- Evidence: `REFRESH_TOKEN_EXPIRE_DAYS = 7` in config.py

**REQ-AUTH-005:** System must support role-based access control (user, admin)
- Status: Implemented
- Evidence: `UserRole` enum in `apps/backend/app/models/user.py`, `require_role` dependency in deps.py

**REQ-AUTH-006:** System must support RS256 algorithm for JWT tokens
- Status: Implemented
- Evidence: RS256 key configuration and selection logic in security.py

### Coaching Sessions

**REQ-COACH-001:** Users must be able to start coaching sessions via WebSocket
- Status: Implemented
- Evidence: `apps/backend/app/api/endpoints/coaching.py`, WebSocket endpoint implementation

**REQ-COACH-002:** System must support four session types: assessment, nudge, reflection, escalation
- Status: Implemented
- Evidence: `SessionType` enum in `apps/backend/app/models/domain.py`

**REQ-COACH-003:** Assessment flow must be a 30-minute structured interview
- Status: Partially Implemented
- Evidence: Assessment flow implemented in `apps/backend/app/services/coaching.py`, but lacks full 30-minute structure

**REQ-COACH-004:** System must enforce WebSocket rate limiting
- Status: Implemented
- Evidence: WebSocket rate limiting in coaching.py with Redis-based counters

**REQ-COACH-005:** System must validate WebSocket message sizes
- Status: Implemented
- Evidence: `WS_MAX_MESSAGE_SIZE = 10000` in coaching.py

### Memory Management

**REQ-MEM-001:** System must store short-term conversation history in Redis
- Status: Implemented
- Evidence: `ShortTermMemory` class in `apps/backend/app/ai/memory_engine/short_term.py`

**REQ-MEM-002:** System must store long-term memories as vectors in Qdrant
- Status: Implemented
- Evidence: `LongTermMemory` class in `apps/backend/app/ai/memory_engine/long_term.py`

**REQ-MEM-003:** System must retrieve relevant memories based on semantic similarity
- Status: Implemented
- Evidence: `retrieve_relevant` method in LongTermMemory with vector search

**REQ-MEM-004:** System must enforce tenant isolation in memory retrieval
- Status: Implemented
- Evidence: User_id filtering in Qdrant queries, tests in `test_memory_integration.py`

### Knowledge Brain (RAG)

**REQ-KB-001:** Users must be able to upload documents (PDF, text)
- Status: Implemented
- Evidence: Document upload endpoint in `apps/backend/app/api/endpoints/documents.py`

**REQ-KB-002:** System must chunk documents into smaller segments
- Status: Implemented
- Evidence: `chunker.py` in `apps/backend/app/ai/knowledge_brain/`

**REQ-KB-003:** System must generate embeddings for document chunks
- Status: Implemented
- Evidence: Embedding providers in `apps/backend/app/ai/embeddings/`

**REQ-KB-004:** System must store embeddings in Qdrant with user isolation
- Status: Implemented
- Evidence: Vector storage with user_id filter in retriever.py

**REQ-KB-005:** System must retrieve relevant chunks for context
- Status: Implemented
- Evidence: `KnowledgeRetriever` class with semantic search

### Goals and Habits

**REQ-GOAL-001:** Users must be able to create, update, and delete goals
- Status: Implemented
- Evidence: Goal model in `apps/backend/app/models/domain.py`, CRUD operations

**REQ-GOAL-002:** System must track goal completion status
- Status: Implemented
- Evidence: `is_completed` field in Goal model

**REQ-GOAL-003:** Users must be able to create habits with frequency
- Status: Implemented
- Evidence: Habit model in `apps/backend/app/models/domain.py`

**REQ-GOAL-004:** System must track habit streak counts
- Status: Implemented
- Evidence: `streak_count` field in Habit model

### Journal Entries

**REQ-JRN-001:** Users must be able to create journal entries
- Status: Implemented
- Evidence: JournalEntry model in `apps/backend/app/models/domain.py`

**REQ-JRN-002:** Users must be able to record mood scores (1-10)
- Status: Implemented
- Evidence: `mood_score` field in JournalEntry model with validation

**REQ-JRN-003:** System must support semantic search of journal entries
- Status: Implemented
- Evidence: Vector search integration with memory system

### AI Agents

**REQ-AGENT-001:** System must provide base agent framework
- Status: Implemented
- Evidence: `BaseAgent` class in `apps/backend/app/ai/agents/base.py`

**REQ-AGENT-002:** System must support routing to specialized agents
- Status: Partially Implemented
- Evidence: `AgentRouter` class with keyword-based routing, but concrete agent implementations not yet created

**REQ-AGENT-003:** System must support 8 agent types: Life Strategist, Mental Wellness, Habit Coach, Learning Coach, Fitness Coach, Career Coach, Financial Coach, Relationship Coach
- Status: Framework Only
- Evidence: `AgentType` enum defines these types, but implementations do not exist

**REQ-AGENT-004:** Agents must be able to execute tools
- Status: Framework Only
- Evidence: Tool registration in BaseAgent, but no agents registered with tools

### Tool Execution

**REQ-TOOL-001:** System must provide tool registry for secure execution
- Status: Implemented
- Evidence: `ToolRegistry` class in `apps/backend/app/ai/tools/registry.py`

**REQ-TOOL-002:** System must validate tool arguments against schemas
- Status: Implemented
- Evidence: `_validate_arguments` method in ToolRegistry

**REQ-TOOL-003:** System must enforce tenant isolation in tool execution
- Status: Implemented
- Evidence: User_id filtering in tool executors, security event logging

**REQ-TOOL-004:** System must support three default tools: check_habit_status, get_goal_progress, get_recent_journals
- Status: Implemented
- Evidence: Tool executors implemented in registry.py

### Rate Limiting

**REQ-RL-001:** System must enforce rate limiting using Redis
- Status: Implemented
- Evidence: Rate limiting middleware in `apps/backend/app/middleware/rate_limit.py`

**REQ-RL-002:** System must support endpoint-specific rate limits
- Status: Implemented
- Evidence: `endpoint_rate_limit.py` with per-endpoint limits

**REQ-RL-003:** System must use sliding window algorithm
- Status: Implemented
- Evidence: Redis sorted sets for sliding window in rate limit middleware

**REQ-RL-004:** System must fail-closed on Redis failure
- Status: Implemented
- Evidence: `RATE_LIMIT_FAIL_OPEN = False` default in config.py

**REQ-RL-005:** System must validate trusted proxy headers
- Status: Implemented
- Evidence: Trusted proxy validation in endpoint_rate_limit.py

## Non-Functional Requirements

### Performance

**REQ-PERF-001:** API response time must be < 500ms for non-AI endpoints
- Status: Verified in tests
- Evidence: Performance benchmarks in test suite

**REQ-PERF-002:** AI response time must be < 5s for coaching interactions
- Status: Not formally verified
- Evidence: No specific performance tests for AI response time

**REQ-PERF-003:** System must support 10M concurrent users
- Status: Architecture designed for, not load tested
- Evidence: Horizontal scaling design in system architecture docs

### Reliability

**REQ-REL-001:** System must have 99.9% uptime
- Status: Not measured
- Evidence: No uptime monitoring configured

**REQ-REL-002:** System must handle database failures gracefully
- Status: Partially Implemented
- Evidence: Health checks with timeout handling, but no circuit breakers

**REQ-REL-003:** System must handle LLM provider failures with fallback
- Status: Framework Only
- Evidence: LLM provider factory supports multiple providers, but no automatic fallback logic

### Security

**REQ-SEC-001:** System must encrypt data at rest
- Status: Partially Implemented
- Evidence: Database encryption depends on provider (MongoDB Atlas encryption-at-rest)

**REQ-SEC-002:** System must encrypt data in transit (TLS)
- Status: Not verified
- Evidence: TLS configuration depends on deployment infrastructure

**REQ-SEC-003:** System must enforce tenant isolation at all layers
- Status: Implemented
- Evidence: User_id filtering in database queries, vector search, and tool execution

**REQ-SEC-004:** System must detect and block prompt injection attacks
- Status: Implemented
- Evidence: `AISecurityValidator` with prompt injection detection

**REQ-SEC-005:** System must sanitize user input before LLM processing
- Status: Implemented
- Evidence: Input sanitization in AISecurityValidator

**REQ-SEC-006:** System must filter LLM output for sensitive content
- Status: Implemented
- Evidence: Output filtering in AISecurityValidator

### Privacy

**REQ-PRIV-001:** System must not expose user data to other tenants
- Status: Implemented
- Evidence: Cross-tenant isolation tests verify data isolation

**REQ-PRIV-002:** System must support user data deletion (GDPR right to be forgotten)
- Status: Not Implemented
- Evidence: No data deletion endpoint or process documented

**REQ-PRIV-003:** System must log security events for compliance
- Status: Implemented
- Evidence: ComplianceEvent model and security event logging in tool registry

### Scalability

**REQ-SCALE-001:** System must support horizontal scaling of API servers
- Status: Architecture supports, not deployed
- Evidence: Stateless API design with external state stores

**REQ-SCALE-002:** System must support database sharding
- Status: Architecture supports, not configured
- Evidence: MongoDB Atlas sharding design in system architecture

**REQ-SCALE-003:** System must use distributed rate limiting
- Status: Implemented
- Evidence: Redis-based rate limiting shared across workers

### Observability

**REQ-OBS-001:** System must export Prometheus metrics
- Status: Implemented
- Evidence: Metrics endpoint and metric definitions in `apps/backend/app/core/metrics.py`

**REQ-OBS-002:** System must provide structured logging
- Status: Implemented
- Evidence: Structured logging configuration in `apps/backend/app/core/logging_config.py`

**REQ-OBS-003:** System must provide health check endpoints
- Status: Implemented
- Evidence: `/health/live`, `/health/ready`, `/health` endpoints in main.py

**REQ-OBS-004:** System must correlate requests with unique IDs
- Status: Implemented
- Evidence: Request ID middleware with UUID generation and propagation

## Acceptance Criteria

### Phase 12.5 (Current State)

**AC-12.5-001:** 832 tests passing
- Status: Met
- Evidence: Phase 12.5 report, commit 4a93c03

**AC-12.5-002:** 0 test failures
- Status: Met
- Evidence: Phase 12.5 report

**AC-12.5-003:** Endpoint-specific rate limiting implemented
- Status: Met
- Evidence: `endpoint_rate_limit.py` with 10+ endpoint limits

**AC-12.5-004:** Multi-worker rate limiting tests passing
- Status: Met
- Evidence: `test_multi_worker_rate_limiting.py` with 8 passing tests

**AC-12.5-005:** Security guarantees preserved
- Status: Met
- Evidence: Phase 12.5 security matrix verification

## Requirement Status Legend

- **Implemented:** Feature is fully implemented and tested
- **Partially Implemented:** Feature is partially implemented with known gaps
- **Framework Only:** Framework exists but concrete implementations are missing
- **Not Implemented:** Feature is not implemented
- **Not Verified:** Feature may be implemented but not formally tested or verified
- **Architecture Supports:** Architecture design supports the feature but it's not yet implemented
