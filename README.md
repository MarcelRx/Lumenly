# Lumenly

AI-powered wellness coaching platform — TurboRepo monorepo.

## Overview

Lumenly is an AI-native life operating system designed to provide personalized wellness coaching through multiple specialized AI agents. The platform integrates memory management, knowledge retrieval, and secure tool execution to deliver context-aware coaching experiences.

## Vision and Goals

**Vision:** To become a comprehensive AI-powered life operating system that helps users achieve their wellness goals through personalized, context-aware coaching.

**Goals:**

- Provide domain-specific coaching across mental health, fitness, career, finance, relationships, and more
- Maintain user privacy through tenant isolation and secure data handling
- Enable scalable multi-tenant architecture for 10M+ users
- Support real-time coaching interactions via WebSocket
- Deliver personalized insights based on user behavior and goals

## Problem

Traditional wellness coaching applications lack:

- Personalized, context-aware AI interactions
- Secure multi-tenant isolation for sensitive data
- Scalable architecture for large user bases
- Integration of memory, knowledge, and tools in a unified system

## Solution

Lumenly provides:

- **Multi-agent AI system** with specialized coaches for different life domains
- **Privacy-first memory architecture** with short-term (Redis) and long-term (Qdrant) storage
- **Knowledge brain (RAG)** for document-based context retrieval
- **Secure tool execution** with tenant isolation and authorization
- **Real-time coaching** via WebSocket with rate limiting
- **Comprehensive testing** with 832+ tests covering security, authorization, and functionality

## System Architecture

Lumenly uses a TurboRepo monorepo structure:

```
Lumenly/
├── apps/
│   ├── backend/          # FastAPI service (Python 3.11+)
│   └── frontend/         # React 19 + TypeScript + Vite web application
├── packages/
│   └── shared/           # OpenAPI specs, JSON schemas, shared contracts
├── docs/                 # Architecture & product documentation
├── infra/                # IaC (Docker Compose, Helm, Terraform)
├── tests/                # Cross-cutting integration & e2e suites
└── scripts/              # Helper scripts (seeding, initialization)
```

### Tech Stack

**Backend:**

- FastAPI (async) for HTTP/WebSocket APIs
- PostgreSQL for user authentication and authorization
- MongoDB Atlas (via Beanie ODM) for domain models (goals, habits, journals, coaching sessions)
- Redis for caching, rate limiting, and short-term memory
- Qdrant for vector storage and semantic search
- Celery for background tasks

**AI/ML:**

- LLM providers: Groq (primary), Gemini (fallback/enterprise)
- Embedding providers: OpenAI, Cohere, FastEmbed, Sentence Transformers
- Custom RAG orchestrator with security validation
- Memory engine with short-term and long-term storage

**Security:**

- JWT authentication (HS256 and RS256 support)
- Role-based access control (RBAC)
- Tenant isolation at database query level
- Redis-based rate limiting (endpoint-specific and global)
- Trusted proxy validation for rate limiting
- Tool registry with authorization and input validation

## Key Features

### Implemented Features

**Backend:**

- **User Authentication:** JWT-based auth with refresh tokens, role-based access control
- **Memory Management:** Short-term (Redis) and long-term (Qdrant) memory with tenant isolation
- **Document Upload:** PDF processing with chunking and embedding for knowledge retrieval
- **Goal & Habit Tracking:** MongoDB-based goal and habit management with streak tracking
- **Journal Entries:** User reflections with mood scoring and vector search
- **AI Insights:** Automated insights generation with TTL-based expiration
- **Rate Limiting:** Redis-based distributed rate limiting with endpoint-specific limits
- **Tool Execution:** Secure tool registry with authorization and tenant isolation
- **Metrics & Observability:** Prometheus metrics for requests, rate limits, and security events
- **RAG Orchestrator:** Retrieval-augmented generation with memory and knowledge retrieval
- **Agent Framework:** Base agent interface and keyword-based router (framework only, no concrete agent implementations)

**Not Yet Implemented (Backend):**

- Coaching Sessions: Assessment, nudge, reflection, and escalation flows via WebSocket
- Concrete specialized agent implementations (Fitness Coach, Habit Coach, etc.) - only the framework exists
- Voice pipeline (ElevenLabs integration)
- Wellness intelligence engine (sensor data integration)
- Personalization engine (user blueprint computation)
- Agent fusion engine for parallel execution
- Data deletion (GDPR right-to-be-forgotten)

**Frontend (Web Application):**

- **Login Screen:** Email/password authentication with JWT token storage
- **Chat Workspace:** HTTP-based AI coaching interface (POST to /api/v1/ai/ask) with multi-agent routing display
- **Knowledge Base Dashboard:** Document management interface
- **Client-Side Routing:** React Router DOM for navigation
- **Authentication State:** Token-based session management with localStorage
- **HTTP Communication:** Uses Axios for HTTP requests to backend API (not WebSocket or polling)

### Planned Features

- **Specialized AI Agents:** Concrete implementations of domain-specific coaches (Fitness Coach, Habit Coach, etc.) - currently only the base agent framework exists
- **Voice Pipeline:** ElevenLabs integration for voice input/output
- **Wellness Intelligence Engine:** Sensor data integration for wellness scoring
- **Personalization Engine:** User blueprint computation from behavior patterns
- **Advanced Agent Orchestration:** Parallel agent execution and fusion engine

## AI Architecture

### Implemented Components

**RAG Orchestrator:**

- Unified retrieval-augmented generation pipeline
- Security validation (prompt injection detection, input sanitization, output filtering)
- Memory retrieval (short-term and long-term)
- Knowledge retrieval from user documents
- Context construction and ranking
- LLM generation with fallback handling

**Memory Engine:**

- Short-term memory: Redis-based conversation history
- Long-term memory: Qdrant-based vector storage with semantic search
- Memory manager orchestrating both layers
- Tenant isolation at vector search level

**Agent System (Framework Only):**

- BaseAgent abstract class defining agent contract
- AgentRouter with keyword-based routing to 8 agent types
- AgentType enum: LIFE_STRATEGIST, MENTAL_WELLNESS, HABIT_COACH, LEARNING_COACH, FITNESS_COACH, CAREER_COACH, FINANCIAL_COACH, RELATIONSHIP_COACH
- **Note:** Concrete agent implementations are not yet implemented - only the framework exists

**Tool Registry:**

- Three registered tools: check_habit_status, get_goal_progress, get_recent_journals
- Tool authorization with role-based access control
- Input validation against JSON schemas
- Tenant isolation enforcement at database query level
- Security event logging for cross-tenant access attempts

**Knowledge Brain:**

- Document chunking with configurable chunk size
- Embedding pipeline with multiple provider support
- Qdrant-based vector storage with user_id filtering
- Semantic search with tenant isolation

### Not Yet Implemented

- Concrete specialized agent implementations (only BaseAgent framework exists)
- Agent fusion engine for parallel execution
- Agent tool calling with function execution
- LLM router with cost-aware model selection
- Voice pipeline with ElevenLabs integration
- Wellness intelligence engine with sensor data
- Personalization engine with user blueprint computation

## Data Architecture

### Data Flow

1. **User Request** → FastAPI endpoint with JWT authentication
2. **Rate Limiting** → Redis-based sliding window check
3. **Context Retrieval** → Memory manager retrieves short-term and long-term memories
4. **Knowledge Retrieval** → Qdrant search for relevant document chunks (if available)
5. **Security Validation** → Prompt injection detection and input sanitization
6. **LLM Generation** → Groq or Gemini provider based on configuration
7. **Response Validation** → Output filtering and safety checks
8. **Memory Persistence** → Conversation turn saved to short-term memory
9. **Response** → JSON response with metadata and context used

### Data Stores

**PostgreSQL:**

- Users table (authentication, roles, email)
- Immutable audit logs (compliance events)

**MongoDB Atlas:**

- Journal entries (user reflections with mood scores)
- Goals (user objectives with completion tracking)
- Habits (recurring activities with streak counts)
- User documents (uploaded files with vector IDs)
- Coaching sessions (session metadata and status)
- AI insights (generated insights with TTL)
- Compliance events (security and audit events)

**Redis:**

- Short-term memory (conversation history)
- Rate limit counters (sliding window)
- Caching layer (profiles, session data)

**Qdrant:**

- Long-term memory vectors (semantic search)
- Knowledge base vectors (document chunks)
- User-scoped collections with tenant isolation

## Testing and Evaluation

### Test Coverage

- **832 tests passing** (as of Phase 12.5, commit 4a93c03)
- **1 xfailed test** (expected failure in test_configuration.py)
- **229 warnings** (non-blocking, mostly deprecations and asyncio marks)

### Test Categories

- Unit tests for individual components
- Integration tests for database interactions
- Security tests for authentication, authorization, and tenant isolation
- Rate limiting tests (endpoint-specific and multi-worker)
- WebSocket coaching tests (adversarial and security)
- AI component tests (memory, RAG, embeddings)
- Architecture regression tests

### Running Tests

```bash
# Run all tests
cd apps/backend
python -m pytest tests/ -v --tb=short --no-header

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=xml --cov-report=term
```

### Linting

```bash
# Run Ruff linter
cd apps/backend
ruff check app/ --fix

# Run Ruff formatter
ruff format app/
```

## Security and Privacy

### Authentication & Authorization

- JWT access tokens (15 min expiration) and refresh tokens (7 days)
- Support for HS256 and RS256 algorithms
- Role-based access control (user, admin)
- Token rotation prevents reuse

### Tenant Isolation

- All database queries include user_id filter
- Vector search in Qdrant uses user_id filter
- Tool execution enforces ownership at database level
- Cross-tenant access attempts logged as security events

### Rate Limiting

- Redis-based distributed rate limiting
- Endpoint-specific limits (login, registration, AI requests, document uploads)
- Per-user and per-IP isolation
- Fail-closed behavior on Redis failure (configurable)
- Trusted proxy validation for X-Forwarded-For headers

### Input Validation & Sanitization

- Prompt injection detection
- Input sanitization before LLM processing
- Output filtering for sensitive content
- Tool argument validation against JSON schemas

### Secrets Management

- Configuration validation rejects placeholder secrets in production
- Environment-specific validation (development, staging, production)
- Secret key length requirements (32+ characters)
- Separate SECRET_KEY and JWT_SECRET required

## Observability and Error Handling

### Metrics

- Prometheus metrics for:
  - HTTP request duration and status codes
  - Rate limit violations
  - WebSocket connections and messages
  - Security events (authorization failures, cross-tenant attempts)
  - Database health status

### Logging

- Structured logging with request correlation IDs
- Request timing tracking
- Error logging with full context server-side
- Safe error messages to clients (stack traces only in development)

### Health Checks

- `/health/live` - Liveness probe (process alive, no external dependencies)
- `/health/ready` - Readiness probe (verifies PostgreSQL, MongoDB, Redis, Qdrant)
- `/health` - Legacy endpoint for backward compatibility

### Error Handling

- Global exception handler with proper observability
- Graceful degradation for non-critical failures
- Timeout handling for database connections (5s)
- Fallback responses when AI components fail

## Deployment and Infrastructure

### Prerequisites

- Node.js >= 20
- npm >= 10
- Python >= 3.11
- Docker (for local development stack)

### Local Development

```bash
# Install dependencies
npm install

# Run all workspaces in dev mode
npm run dev

# Build all workspaces
npm run build
```

### Infrastructure Services

- PostgreSQL 15 (authentication, audit logs)
- MongoDB 7 (domain models)
- Redis 7 (caching, rate limiting, short-term memory)
- Qdrant (vector storage)

### CI/CD

- GitHub Actions for CI (test, lint, security scan, build)
- Tests run against PostgreSQL, MongoDB, Redis, and Qdrant services
- Docker image build and test
- TruffleHog for secret scanning

### Configuration

Environment variables required (see `apps/backend/.env` for example):

- `SECRET_KEY`, `JWT_SECRET` (and RS256 keys if using RS256)
- `POSTGRES_URL`, `MONGODB_URL`, `REDIS_URL`, `QDRANT_URL`
- `GROQ_API_KEY` or `GEMINI_API_KEY` (at least one required)
- `OPENAI_API_KEY` or `COHERE_API_KEY` (for embeddings)
- `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `VECTOR_DIMENSION`
- Rate limiting configuration

## Engineering Challenges

### Current Limitations

- No concrete agent implementations (only framework exists)
- Knowledge base collection may not exist in all environments
- No voice pipeline implementation
- No wellness intelligence engine (sensor data integration)
- No personalization engine (user blueprint computation)
- Agent routing is keyword-based (not ML-based)

### Known Issues

- 229 warnings in test suite (mostly deprecations and asyncio marks)
- Some third-party library deprecations (PyPDF2, pythonjsonlogger, redis.setex)
- JWT key length warnings in test fixtures (test-only, not production)

## What I Learned

From the Phase 12.5 implementation:

- Redis-based rate limiting with sliding window algorithm is effective for distributed systems
- Endpoint-specific limits provide better security than global limits
- Fail-closed behavior is critical for security but requires proper monitoring
- Tenant isolation must be enforced at multiple layers (application, database, vector store)
- Tool registry with authorization provides a secure foundation for AI agent capabilities

## Roadmap

See [docs/Roadmap.md](./docs/Roadmap.md) for the full development roadmap (phases 0–15).

## AI-Assisted Development

This repository uses AI-assisted development with governance documented in:

- [docs/ai-development/agent-workflow.md](./docs/ai-development/agent-workflow.md)
- [docs/ai-development/verification-policy.md](./docs/ai-development/verification-policy.md)

## Documentation

For detailed architecture and implementation information, see:

- [docs/product/vision.md](./docs/product/vision.md) - Product vision and requirements
- [docs/architecture/system-architecture.md](./docs/architecture/system-architecture.md) - System architecture
- [docs/architecture/ai-architecture.md](./docs/architecture/ai-architecture.md) - AI architecture and components
- [docs/architecture/agent-orchestration.md](./docs/architecture/agent-orchestration.md) - Agent responsibilities and orchestration
- [docs/architecture/data-flow.md](./docs/architecture/data-flow.md) - Data architecture and flows
- [docs/decisions/README.md](./docs/decisions/README.md) - Architecture Decision Records
- [docs/engineering/testing-and-evaluation.md](./docs/engineering/testing-and-evaluation.md) - Testing and evaluation
- [docs/engineering/observability.md](./docs/engineering/observability.md) - Observability and monitoring
- [docs/engineering/error-handling.md](./docs/engineering/error-handling.md) - Error handling strategies
- [docs/security/security-and-privacy.md](./docs/security/security-and-privacy.md) - Security and privacy
- [docs/deployment/deployment-and-infrastructure.md](./docs/deployment/deployment-and-infrastructure.md) - Deployment and infrastructure

## License

Proprietary — Lumenly Engineering Team.
