# Lumenly System Architecture

## Overview

Lumenly is a TurboRepo monorepo containing a FastAPI backend service and a React Native frontend application. The backend is an AI-native life operating system that integrates multiple AI components including memory management, knowledge retrieval, and agent orchestration.

## Application Boundaries

### Backend Service (`apps/backend/`)

**Responsibilities:**

- HTTP/WebSocket API endpoints
- Authentication and authorization
- AI component orchestration (RAG, memory, agents)
- Business logic for coaching, goals, habits, journals
- Rate limiting and security middleware

**Technology Stack:**

- FastAPI (async Python framework)
- Beanie ODM (async MongoDB ORM)
- SQLAlchemy (async PostgreSQL ORM)
- Redis (caching and rate limiting)
- Qdrant (vector storage)

### Frontend Application (`apps/frontend/`)

**Responsibilities:**

- User interface for coaching interactions
- Document upload and management
- User authentication and session management
- HTTP client for backend API communication

**Technology Stack:**

- React 19 + TypeScript + Vite (web application)
- React Router DOM for client-side routing
- Axios for HTTP requests
- Tailwind CSS for styling
- Lucide React for icons

**Implemented Screens:**

- Login page (`/login`) - Email/password authentication
- Chat workspace (`/`) - AI coaching interface with HTTP-based chat
- Knowledge Base dashboard (`/kb`) - Document management

**Current Limitations:**

- Uses HTTP polling for chat (not WebSocket)
- No goal/habit tracking UI implemented
- No journal entry UI implemented
- No wellness dashboard implemented
- Only 3 screens total (minimal implementation)

### Shared Packages (`packages/shared/`)

**Responsibilities:**

- OpenAPI specifications
- JSON schemas for data contracts
- Shared type definitions

## Main Components

### API Layer

**Location:** `apps/backend/app/api/`

**Endpoints:**

- `/api/v1/auth/*` - Authentication (login, register, refresh)
- `/api/v1/users/*` - User management
- `/api/v1/documents/*` - Document upload and management
- `/api/v1/journals/*` - Journal entries
- `/api/v1/memory/*` - Memory management
- `/api/v1/vectors/*` - Vector operations
- `/v1/ai/*` - AI endpoints
- `/v1/coaching/*` - Coaching WebSocket and HTTP endpoints
- `/v1/metrics` - Prometheus metrics

**Dependencies:**

- Authentication: JWT tokens, PostgreSQL user store
- Authorization: Role-based access control (RBAC)
- Rate Limiting: Redis-based distributed limiting

### AI Components

**Location:** `apps/backend/app/ai/`

**Sub-components:**

1. **Agent System** (`agent_system/`)
   - Router: Keyword-based routing to 8 agent types
   - Fusion: Agent response fusion (framework only)
   - Prompts: Agent prompt templates
   - Schemas: Agent type definitions

2. **Agents** (`agents/`)
   - Base: Abstract base class for all agents
   - Note: Concrete agent implementations not yet created

3. **LLM Interface** (`llm/`)
   - Interface: Abstract LLM provider interface
   - Providers: Groq, Gemini, Mock implementations
   - Metrics: LLM usage metrics

4. **Embeddings** (`embeddings/`)
   - Interface: Abstract embedding provider interface
   - Providers: OpenAI, Cohere, FastEmbed, Sentence Transformers
   - Sync providers: Synchronous variants

5. **Memory Engine** (`memory_engine/`)
   - Manager: Orchestrates short-term and long-term memory
   - Short-term: Redis-based conversation history
   - Long-term: Qdrant-based vector storage

6. **Memory** (`memory/`)
   - Behavior: Memory behavior patterns
   - Consolidation: Memory consolidation logic
   - Forgetting: Memory decay and forgetting curves
   - Interfaces: Memory interfaces
   - Manager: Memory management
   - Ranking: Memory ranking algorithms
   - Retriever: Memory retrieval
   - Security: Memory security and tenant isolation
   - Storage: Memory storage
   - Summary: Memory summarization
   - Validation: Memory validation

7. **Knowledge Brain** (`knowledge_brain/`)
   - Chunker: Document chunking
   - Ingestor: Document ingestion pipeline
   - Retriever: Knowledge retrieval with tenant isolation

8. **RAG** (`rag/`)
   - Orchestrator: Unified RAG pipeline with security validation

9. **Orchestration** (`orchestration/`)
   - Router: AI orchestration router

10. **Tools** (`tools/`)
    - Registry: Secure tool execution with authorization

11. **Security** (`security.py`)
    - AI security validator with prompt injection detection

### Database Layer

**Location:** `apps/backend/app/db/`

**Components:**

- PostgreSQL: User authentication and authorization
- MongoDB: Domain models (goals, habits, journals, coaching sessions, documents, insights, compliance events)
- Redis: Caching, rate limiting, short-term memory
- Qdrant: Vector storage for long-term memory and knowledge base

### Models

**Location:** `apps/backend/app/models/`

**PostgreSQL Models:**

- User: Authentication, roles, email, password hash

**MongoDB Models (Beanie ODM):**

- JournalEntry: User reflections with mood scores
- Goal: User objectives with completion tracking
- Habit: Recurring activities with streak counts
- UserDocument: Uploaded files with vector IDs
- CoachingSession: Session metadata and status
- AIInsight: Generated insights with TTL
- ComplianceEvent: Security and audit events

### Middleware

**Location:** `apps/backend/app/middleware/`

**Components:**

- Metrics: Prometheus metrics collection
- Rate Limit: Global rate limiting
- Endpoint Rate Limit: Endpoint-specific rate limiting

### Services

**Location:** `apps/backend/app/services/`

**Components:**

- Coaching: Coaching flow service (assessment, nudge, reflection, escalation)
- LLM: LLM service layer
- Vector: Vector service layer

### Core

**Location:** `apps/backend/app/core/`

**Components:**

- Config: Application configuration with validation
- Logging: Structured logging configuration
- Metrics: Prometheus metric definitions
- Security: JWT token generation and validation
- Celery App: Background task configuration
- Beat Config: Celery beat scheduler configuration

## Important Interfaces

### Authentication Flow

1. User registers with email/password → PostgreSQL User record created
2. User logs in → JWT access token (15 min) and refresh token (7 days) generated
3. Access token included in Authorization header → Token validated on each request
4. Refresh token used to obtain new access token → Token rotation prevents reuse

### Authorization Flow

1. Request includes JWT access token
2. Token decoded to extract user_id
3. User record fetched from PostgreSQL
4. Role checked against endpoint requirements (if any)
5. User context propagated to handlers

### Coaching Flow

1. User initiates WebSocket connection with JWT token
2. WebSocket rate limits checked (connection, message, tool call)
3. Coaching session created in MongoDB
4. Agent router determines appropriate agent type
5. Memory manager retrieves relevant context
6. LLM generates response
7. Response sent over WebSocket
8. Conversation turn saved to memory

### Document Ingestion Flow

1. User uploads document via HTTP endpoint
2. Document stored in MongoDB UserDocument collection
3. Document chunked into segments
4. Each chunk embedded using embedding provider
5. Vectors stored in Qdrant with user_id filter
6. Vector IDs stored in MongoDB document

### Memory Retrieval Flow

1. Query embedded using embedding provider
2. Short-term memory retrieved from Redis (last N messages)
3. Long-term memory retrieved from Qdrant (top-k semantic matches)
4. Results fused and ranked
5. Context passed to LLM for generation

## External Services

### PostgreSQL

- **Purpose:** User authentication, authorization, audit logs
- **Connection:** Async SQLAlchemy with connection pooling
- **Collections:** users (authentication)

### MongoDB Atlas

- **Purpose:** Domain models, compliance events
- **Connection:** Async Motor (Beanie ODM)
- **Collections:** journal_entries, goals, habits, user_documents, coaching_sessions, ai_insights, compliance_events

### Redis

- **Purpose:** Caching, rate limiting, short-term memory
- **Connection:** Async Redis client
- **Uses:** Session storage, rate limit counters, conversation history

### Qdrant

- **Purpose:** Vector storage for long-term memory and knowledge base
- **Connection:** Async Qdrant client
- **Collections:** memory_vectors (per-user), knowledge_base (per-user)

### LLM Providers

- **Groq:** Primary LLM provider (llama-3.3-70b-versatile)
- **Gemini:** Fallback/enterprise provider (gemini-2.5-flash)
- **Mock:** Test environment provider

### Embedding Providers

- **OpenAI:** text-embedding-3-small (1536 dimensions)
- **Cohere:** embed-english-v3.0 (1024 dimensions)
- **FastEmbed:** BAAI/bge-small-en-v1.5 (384 dimensions)
- **Sentence Transformers:** all-MiniLM-L6-v2 (384 dimensions)
- **Mock:** Test environment provider

## Authentication and Authorization Boundaries

### Authentication

- JWT access tokens with 15-minute expiration
- JWT refresh tokens with 7-day expiration
- Support for HS256 and RS256 algorithms
- Token rotation prevents reuse

### Authorization

- Role-based access control (user, admin)
- Admin-only endpoints protected with `require_role` dependency
- User context extracted from token and validated against database

### Tenant Isolation

- All database queries include user_id filter
- Vector search in Qdrant uses user_id filter
- Tool execution enforces ownership at database level
- Cross-tenant access attempts logged as security events

## Deployment Topology

**Current State:** Local development with Docker Compose

**Planned State:** Kubernetes deployment with:

- Horizontal scaling of FastAPI workers
- Redis cluster for distributed caching
- MongoDB Atlas sharding for scalability
- Qdrant sharding for vector storage
- PostgreSQL with connection pooling

**Current Deployment Configuration:**

- Services defined in `infra/docker-compose.yml`
- No production deployment configuration verified
- CI/CD pipeline builds Docker images but does not deploy

## Architectural Diagrams

### High-Level Architecture

```
┌─────────────┐
│   Frontend  │ (React Native / Expo)
└──────┬──────┘
       │ HTTP/WebSocket
       ▼
┌─────────────────────────────────────┐
│         FastAPI Backend             │
│  ┌───────────────────────────────┐  │
│  │  API Layer (FastAPI Routes)  │  │
│  └───────────┬───────────────────┘  │
│              │                      │
│  ┌───────────▼───────────────────┐  │
│  │  Middleware (Auth, Rate Limit)│  │
│  └───────────┬───────────────────┘  │
│              │                      │
│  ┌───────────▼───────────────────┐  │
│  │  Services (Coaching, etc.)   │  │
│  └───────────┬───────────────────┘  │
│              │                      │
│  ┌───────────▼───────────────────┐  │
│  │  AI Components                │  │
│  │  - RAG Orchestrator           │  │
│  │  - Memory Manager             │  │
│  │  - Agent Router               │  │
│  │  - Tool Registry              │  │
│  └───────────┬───────────────────┘  │
└──────────────┼──────────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌───────┐  ┌───────┐  ┌───────┐
│  PG   │  │  Mongo│  │ Redis │
└───────┘  └───────┘  └───────┘
                │
                ▼
           ┌───────┐
           │ Qdrant│
           └───────┘
```

### Data Flow

```
User Request
    │
    ├─► Authentication (JWT)
    │
    ├─► Rate Limiting (Redis)
    │
    ├─► Context Retrieval
    │   ├─► Short-term Memory (Redis)
    │   └─► Long-term Memory (Qdrant)
    │
    ├─► Knowledge Retrieval (Qdrant, if available)
    │
    ├─► Security Validation
    │   ├─► Prompt Injection Detection
    │   ├─► Input Sanitization
    │   └─► User Access Validation
    │
    ├─► Agent Routing (keyword-based)
    │
    ├─► LLM Generation (Groq/Gemini)
    │
    ├─► Response Validation
    │   └─► Output Filtering
    │
    ├─► Memory Persistence
    │   └─► Save Conversation Turn
    │
    └─► Response to User
```

## Security Boundaries

### Network Security

- CORS configuration with origin validation
- Trusted proxy validation for rate limiting
- No wildcard origins in production

### Application Security

- JWT token validation on all protected endpoints
- Input validation and sanitization
- Output filtering for sensitive content
- Prompt injection detection

### Data Security

- Tenant isolation at database query level
- Vector search with user_id filtering
- Tool execution with ownership enforcement
- Security event logging for compliance

### Infrastructure Security

- Configuration validation rejects placeholder secrets in production
- Environment-specific validation (development, staging, production)
- Secret key length requirements (32+ characters)
- Fail-closed behavior on Redis failure

## Known Limitations

1. **Agent Implementations:** Only base agent framework exists; concrete specialized agents not implemented
2. **Voice Pipeline:** No voice input/output implementation
3. **Wellness Intelligence:** No sensor data integration
4. **Personalization Engine:** No user blueprint computation
5. **Deployment:** No verified production deployment configuration
6. **Monitoring:** No distributed tracing or advanced observability
7. **Circuit Breakers:** No circuit breaker pattern for external service failures
8. **Data Deletion:** No GDPR right-to-be-forgotten implementation
