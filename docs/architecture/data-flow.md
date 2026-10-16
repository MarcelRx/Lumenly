# Lumenly Data Architecture and Flow

## Overview

Lumenly's data architecture spans multiple storage systems (PostgreSQL, MongoDB, Redis, Qdrant) with specific responsibilities for each. Data flows through the system from user input to AI processing to persistence and response generation.

## Data Producers and Consumers

### Data Producers

**Frontend Application:**
- User authentication requests (login, register)
- Coaching interactions (WebSocket messages)
- Document uploads
- Goal and habit updates
- Journal entries
- Profile updates

**AI Components:**
- LLM-generated responses
- AI insights
- Memory consolidation (planned, not implemented)
- Agent decisions (when agents are implemented)

**Background Workers (Planned):**
- Embedding jobs for document processing
- Analytics computations
- Nudge generation
- Insight generation

### Data Consumers

**API Endpoints:**
- Authentication endpoints
- Coaching endpoints
- Document endpoints
- Memory endpoints
- Vector endpoints
- Metrics endpoints

**AI Components:**
- RAG Orchestrator (consumes memory, knowledge)
- Agent System (consumes context, tools)
- Memory Engine (consumes conversation turns)
- Knowledge Brain (consumes documents)

**External Systems:**
- LLM providers (Groq, Gemini)
- Embedding providers (OpenAI, Cohere, etc.)

## API and Internal Interfaces

### HTTP API Endpoints

**Authentication Endpoints (`/api/v1/auth/*`):**
- POST `/register` - User registration
- POST `/login` - User login (returns JWT tokens)
- POST `/refresh` - Refresh access token
- GET `/me` - Get current user info

**User Endpoints (`/api/v1/users/*`):**
- GET `/users/{id}` - Get user by ID
- PUT `/users/{id}` - Update user

**Document Endpoints (`/api/v1/documents/*`):**
- POST `/documents` - Upload document
- GET `/documents/{id}` - Get document
- GET `/documents` - List user documents
- DELETE `/documents/{id}` - Delete document

**Journal Endpoints (`/api/v1/journals/*`):**
- POST `/journals` - Create journal entry
- GET `/journals/{id}` - Get journal entry
- GET `/journals` - List user journals
- PUT `/journals/{id}` - Update journal entry
- DELETE `/journals/{id}` - Delete journal entry

**Memory Endpoints (`/api/v1/memory/*`):**
- POST `/memory/store` - Store memory
- POST `/memory/retrieve` - Retrieve memories
- DELETE `/memory/{id}` - Delete memory

**Vector Endpoints (`/api/v1/vectors/*`):**
- POST `/vectors/embed` - Generate embedding
- POST `/vectors/search` - Vector search

**AI Endpoints (`/v1/ai/*`):**
- POST `/ai/ask` - Ask AI question
- POST `/ai/generate` - Generate text

**Coaching Endpoints (`/v1/coaching/*`):**
- WebSocket `/coaching/ws` - Real-time coaching
- POST `/coaching/sessions` - Create coaching session
- GET `/coaching/sessions/{id}` - Get coaching session
- GET `/coaching/sessions` - List coaching sessions
- POST `/coaching/insights` - Request insights

**Metrics Endpoints (`/v1/metrics`):**
- GET `/metrics` - Prometheus metrics

### WebSocket Interface

**Coaching WebSocket (`/v1/coaching/ws`):**
- Connection requires JWT authentication
- Messages rate-limited (60 per minute)
- Tool calls rate-limited (10 per minute)
- Message size limited (10,000 characters)
- Tool argument size limited (5,000 characters)

**Message Types:**
- User messages (text input)
- Assistant messages (AI responses)
- Tool calls (function execution)
- Tool results (function outputs)
- System messages (status, errors)

### Internal Interfaces

**Memory Manager Interface:**
- `build_context(user_id, query, query_vector)` - Build context for AI
- `save_turn(user_id, user_query, assistant_response)` - Save conversation turn
- `retrieve_memories(user_id, query, config)` - Retrieve relevant memories

**RAG Orchestrator Interface:**
- `process_query(user_id, query, enable_memory, enable_knowledge)` - Process RAG query
- `health_check()` - Check component health

**Tool Registry Interface:**
- `execute_tool(tool_name, arguments, user_id, user_role)` - Execute tool
- `list_tools()` - List registered tools
- `is_tool_registered(tool_name)` - Check tool registration

## Data Transformations and Validation

### Authentication Flow

**Transformations:**
1. User password → bcrypt hash (before storage)
2. User email → lowercase (for consistency)
3. JWT payload → encoded token (HS256 or RS256)
4. Token expiration → timestamp calculation

**Validation:**
- Email format validation
- Password strength validation (8+ characters)
- Token signature validation
- Token expiration check
- Token rotation (refresh token used once)

**Evidence:**
- `apps/backend/app/core/security.py`
- `apps/backend/app/api/endpoints/auth.py`

### Document Ingestion Flow

**Transformations:**
1. Raw file → text extraction (PDF parsing)
2. Text → chunks (configurable size and overlap)
3. Chunks → embeddings (vector generation)
4. Embeddings → Qdrant vectors (with metadata)
5. Document metadata → MongoDB UserDocument

**Validation:**
- File type validation (PDF, text)
- File size validation
- Chunk size validation
- Embedding dimension validation
- User ownership validation

**Evidence:**
- `apps/backend/app/ai/knowledge_brain/chunker.py`
- `apps/backend/app/ai/knowledge_brain/ingestor.py`
- `apps/backend/app/api/endpoints/documents.py`

### Memory Storage Flow

**Transformations:**
1. Conversation turn → Redis list entry (short-term)
2. Conversation turn → embedding (vector generation)
3. Embedding → Qdrant vector (long-term)
4. Metadata → MongoDB memory_links (if implemented)

**Validation:**
- User ownership validation
- Message size validation
- Embedding dimension validation
- Tenant isolation validation

**Evidence:**
- `apps/backend/app/ai/memory_engine/short_term.py`
- `apps/backend/app/ai/memory_engine/long_term.py`
- `apps/backend/app/ai/memory_engine/manager.py`

### Tool Execution Flow

**Transformations:**
1. Tool arguments → JSON schema validation
2. User context → database query filters
3. Database results → tool response format
4. Security events → ComplianceEvent records

**Validation:**
- Tool registration validation
- Argument schema validation
- Authorization validation
- Tenant isolation validation
- Argument size validation

**Evidence:**
- `apps/backend/app/ai/tools/registry.py`

## Persistence and Retrieval

### PostgreSQL

**Collections:**
- users (authentication, roles, email, password hash)

**Persistence:**
- User records created on registration
- User records updated on profile changes
- No soft-delete implementation

**Retrieval:**
- User lookup by email (authentication)
- User lookup by ID (authorization)
- Role-based queries (admin endpoints)

**Indexing:**
- Unique index on email
- Index on id (primary key)

**Evidence:**
- `apps/backend/app/models/user.py`
- `apps/backend/app/db/postgres.py`

### MongoDB Atlas

**Collections:**

**journal_entries:**
- Fields: user_id, content, mood_score, created_at
- Indexes: user_id, created_at, compound (user_id, created_at)
- TTL: None (indefinite retention)

**goals:**
- Fields: user_id, title, description, target_date, is_completed, created_at
- Indexes: user_id, target_date, is_completed, compound (user_id, is_completed, target_date)
- TTL: None (indefinite retention)

**habits:**
- Fields: user_id, title, frequency, streak_count, created_at
- Indexes: user_id, frequency, compound (user_id, frequency, streak_count)
- TTL: None (indefinite retention)

**user_documents:**
- Fields: user_id, filename, content, vector_ids, status, chunk_count, error_message, created_at
- Indexes: user_id, filename, status
- TTL: None (indefinite retention)

**coaching_sessions:**
- Fields: user_id, session_type, agent_id, title, status, metadata, started_at, ended_at, created_at
- Indexes: user_id, session_type, status, compound (user_id, started_at), compound (user_id, status)
- TTL: None (indefinite retention)

**ai_insights:**
- Fields: user_id, insight_type, pillar, payload, confidence, session_id, generated_at, expires_at, created_at
- Indexes: user_id, insight_type, pillar, compound (user_id, insight_type, generated_at), expires_at (TTL)
- TTL: 90 days (via expires_at field)

**compliance_events:**
- Fields: user_id, event_type, severity_level, session_id, details, created_at
- Indexes: user_id, event_type, severity_level, compound (user_id, event_type, created_at), created_at
- TTL: None (indefinite retention for compliance)

**Persistence:**
- Documents created via Beanie ODM
- Updates use Beanie's update methods
- Soft-delete not implemented (except ai_insights via expires_at)

**Retrieval:**
- Queries use user_id filter for tenant isolation
- Compound indexes for efficient multi-field queries
- TTL index for ai_insights expiration

**Evidence:**
- `apps/backend/app/models/domain.py`
- `apps/backend/app/db/mongo.py`

### Redis

**Keys and Patterns:**

**Short-term Memory:**
- Pattern: `short_term_memory:{user_id}`
- Type: List
- TTL: None (indefinite)
- Operations: LPUSH, LRANGE, LTRIM

**Rate Limiting:**
- Pattern: `rate_limit:{user_id}` (global)
- Pattern: `rate_limit:{endpoint}:{user_id}` (endpoint-specific)
- Pattern: `rate_limit:{endpoint}:{ip}` (for anonymous)
- Type: Sorted Set (sliding window)
- TTL: window + 10 seconds
- Operations: ZADD, ZREMRANGEBYSCORE, ZCARD

**WebSocket Rate Limiting:**
- Pattern: `ws_connection:{user_id}`
- Pattern: `ws_message:{user_id}`
- Pattern: `ws_tool_call:{user_id}`
- Type: Sorted Set (sliding window)
- TTL: window + 10 seconds
- Operations: ZADD, ZREMRANGEBYSCORE, ZCARD

**Caching:**
- Pattern: `cache:{key}` (not currently used)
- Type: String or Hash
- TTL: Configurable per cache entry

**Persistence:**
- Redis AOF (Append Only File) for durability
- Configuration depends on deployment

**Retrieval:**
- Direct key access
- Pattern-based queries not used (specific keys only)

**Evidence:**
- `apps/backend/app/ai/memory_engine/short_term.py`
- `apps/backend/app/middleware/rate_limit.py`
- `apps/backend/app/middleware/endpoint_rate_limit.py`
- `apps/backend/app/api/endpoints/coaching.py`

### Qdrant

**Collections:**

**Memory Vectors:**
- Collection: Per-user collections or single collection with user_id filter
- Fields: vector, user_id, content, timestamp
- Indexing: Vector index (HNSW), payload index on user_id
- TTL: None (indefinite)

**Knowledge Base:**
- Collection: knowledge_base
- Fields: vector, user_id, document_title, chunk_text
- Indexing: Vector index (HNSW), payload index on user_id
- TTL: None (indefinite)

**Persistence:**
- Vectors stored with metadata
- Upsert operations for updates
- No soft-delete implementation

**Retrieval:**
- Semantic search with query_points
- User_id filter for tenant isolation
- Top-k results with scores

**Evidence:**
- `apps/backend/app/ai/memory_engine/long_term.py`
- `apps/backend/app/ai/knowledge_brain/retriever.py`
- `apps/backend/app/db/qdrant.py`

## Tenant Boundaries

### User Isolation

**PostgreSQL:**
- User queries always include user_id or email filter
- No cross-user queries allowed
- Role-based access for admin endpoints

**MongoDB:**
- All queries include user_id filter
- Cross-tenant access attempts logged as security events
- Generic error messages to prevent enumeration

**Redis:**
- Keys include user_id for isolation
- No cross-user key access
- Rate limiting per-user

**Qdrant:**
- Vector search includes user_id filter
- Per-user collections or user_id payload filter
- Cross-tenant access blocked at query level

**Evidence:**
- Database queries in all repository files
- Security tests in `test_cross_tenant_authorization.py`
- Tool registry security in `apps/backend/app/ai/tools/registry.py`

## Data Ownership

**User Data:**
- Users own their own data (goals, habits, journals, documents, memories)
- Data cannot be accessed by other users
- Admin access for compliance and support

**System Data:**
- Compliance events owned by system
- AI insights generated for users but owned by system
- Coaching sessions owned by users but metadata accessible to system

**Shared Data:**
- No shared data between users
- No global data stores

## Error and Retry Paths

### Database Connection Failures

**PostgreSQL:**
- Connection pool with retry logic
- Health check with 5-second timeout
- Fails health check if unavailable
- No circuit breaker

**MongoDB:**
- Async Motor with retry logic
- Health check with 5-second timeout
- Fails health check if unavailable
- No circuit breaker

**Redis:**
- Async Redis client with retry logic
- Health check with 5-second timeout
- Rate limiting fails-closed on Redis failure
- No circuit breaker

**Qdrant:**
- Async Qdrant client with retry logic
- Health check with 5-second timeout
- Fails health check if unavailable
- No circuit breaker

**Evidence:**
- Health checks in `apps/backend/app/main.py`
- Database connection code in `apps/backend/app/db/`

### LLM Provider Failures

**Groq:**
- Provider-specific error handling
- No automatic fallback to Gemini
- Error propagated to caller
- Orchestrator may provide fallback response

**Gemini:**
- Provider-specific error handling
- No automatic fallback to Groq
- Error propagated to caller
- Orchestrator may provide fallback response

**Evidence:**
- Provider implementations in `apps/backend/app/ai/llm/`
- Orchestrator fallback in `apps/backend/app/ai/orchestration/router.py`

### Embedding Provider Failures

**OpenAI/Cohere/FastEmbed/Sentence Transformers:**
- Provider-specific error handling
- No automatic fallback between providers
- Error propagated to caller
- Document ingestion fails on embedding failure

**Evidence:**
- Provider implementations in `apps/backend/app/ai/embeddings/`

## Sensitive Data Handling

### Data at Rest

**PostgreSQL:**
- Encryption depends on provider (PostgreSQL encryption-at-rest)
- Passwords bcrypt hashed (one-way)
- No PII in plain text (except email)

**MongoDB:**
- Encryption-at-rest via MongoDB Atlas
- No PII in vector payloads (user_id only)
- Journal content may contain sensitive information

**Redis:**
- No encryption by default
- Short-term memory may contain sensitive conversation history
- Encryption depends on deployment

**Qdrant:**
- Encryption-at-rest via Qdrant or deployment
- Vector payloads contain hashed identifiers only
- No PII in vector payloads

### Data in Transit

**HTTP/WebSocket:**
- TLS encryption depends on deployment
- No TLS configuration verified in code
- Depends on reverse proxy or load balancer

**Database Connections:**
- TLS depends on connection string configuration
- Not verified in current implementation

### Logging

**Structured Logging:**
- Request IDs for correlation
- Error logging with full context server-side
- No PII in logs (user_id only)
- Stack traces only in development

**Evidence:**
- Logging configuration in `apps/backend/app/core/logging_config.py`
- Request correlation in `apps/backend/app/main.py`

## Retention and Deletion Behavior

### Implemented Retention

**AI Insights:**
- 90-day TTL via expires_at field
- MongoDB TTL index on expires_at
- Automatic expiration

**Rate Limiting:**
- Redis keys expire after window + 10 seconds
- Automatic cleanup

**Compliance Events:**
- No TTL (indefinite retention for compliance)

### Not Implemented

**User Data Deletion (GDPR):**
- No right-to-be-forgotten endpoint
- No data deletion process
- No data retention policy enforcement

**Journal Entries:**
- No TTL (indefinite retention)
- Planned 180-day retention (not implemented)

**Conversation History:**
- No TTL (indefinite retention in Redis)
- No archival process

**Documents:**
- No TTL (indefinite retention)
- No archival process

**Evidence:**
- TTL index on ai_insights in `apps/backend/app/models/domain.py`
- No deletion endpoints found

## Data Flow Diagrams

### Authentication Flow

```
User → POST /api/v1/auth/login
  ↓
Validate credentials
  ↓
Generate JWT tokens (access + refresh)
  ↓
Return tokens to user
  ↓
User includes access token in Authorization header
  ↓
API validates token on each request
  ↓
User context extracted and propagated
```

### Coaching Flow

```
User → WebSocket connection with JWT
  ↓
Validate JWT and check rate limits
  ↓
Create CoachingSession in MongoDB
  ↓
User sends message
  ↓
AgentRouter routes to agent type
  ↓
MemoryManager retrieves context (Redis + Qdrant)
  ↓
LLM generates response
  ↓
Response sent over WebSocket
  ↓
Conversation turn saved to Redis
  ↓
(Optional) Memory stored in Qdrant
```

### Document Ingestion Flow

```
User → POST /api/v1/documents
  ↓
File uploaded and stored
  ↓
Document record created in MongoDB (status: PENDING)
  ↓
Background job: chunk document
  ↓
Background job: generate embeddings
  ↓
Vectors stored in Qdrant with user_id filter
  ↓
Document record updated (status: PROCESSED, vector_ids populated)
  ↓
Return document ID to user
```

### Memory Retrieval Flow

```
Query received
  ↓
Generate query embedding
  ↓
Retrieve short-term memory from Redis (last N messages)
  ↓
Retrieve long-term memory from Qdrant (top-k semantic matches)
  ↓
Fuse and rank results
  ↓
Build context for LLM
  ↓
LLM generates response with context
  ↓
Return response to user
```

### Tool Execution Flow

```
Agent decides to use tool
  ↓
ToolRegistry.validate_arguments()
  ↓
ToolRegistry.check_authorization()
  ↓
Tool executor called with user_id
  ↓
Database query with user_id filter
  ↓
Results returned or security event logged
  ↓
Tool result returned to agent
```

## Known Limitations

1. **No Data Deletion:** GDPR right-to-be-forgotten not implemented
2. **No Data Retention Policy:** Most data retained indefinitely
3. **No Data Archival:** No process for archiving old data
4. **No Circuit Breakers:** No circuit breaker pattern for external services
5. **TLS Not Verified:** Encryption in transit depends on deployment
6. **Redis Encryption:** No encryption by default
7. **No Backup/Restore:** No documented backup/restore process
