---
title: Lumenly – Master Development Roadmap
author: VP of Engineering / Technical Program Manager / Principal Software Architect
date: 2026-06-20
version: 1.0
status: APPROVED FOR EXECUTION
classification: INTERNAL — ENGINEERING LEADERSHIP
---

# Lumenly — Master Development Roadmap

> **Purpose**: This document is the single source of truth for building Lumenly from an empty repository to a production-ready AI-native Life Operating System. It covers MVP (Q4 2026), V1 (Q2 2027), and the engineering scaffolding required for the Enterprise tier (Q4 2027). Every phase, deliverable, and task flows directly from the approved PRD, System Architecture, Database Design, Project Structure, AI System Design, and API Contracts documents.

---

## How to Read This Roadmap

Each phase contains a **Phase Summary** (Goal, Deliverables, Dependencies, Complexity, Duration, Acceptance Criteria) followed by a **Task Breakdown Table**. Tasks are sequenced within each phase; a task's dependencies list the Task IDs that must be complete before it can begin. Phases themselves are largely sequential, though some parallel tracks are called out explicitly.

**Effort notation**: S = Small (1–2 days), M = Medium (3–5 days), L = Large (6–10 days), XL = Extra-Large (2+ weeks).

**Owner types**: BE = Backend, FE = Frontend, AI = AI/ML, DO = DevOps, QA = Quality Assurance.

---

## Roadmap at a Glance

| Phase | Name                   | Duration | Complexity  | MVP Gate |
| ----- | ---------------------- | -------- | ----------- | -------- |
| 0     | Repository Foundation  | 1 week   | Low         | ✓        |
| 1     | Backend Foundation     | 2 weeks  | Medium      | ✓        |
| 2     | Authentication & Users | 2 weeks  | Medium      | ✓        |
| 3     | Conversations          | 2 weeks  | Medium      | ✓        |
| 4     | Memory Engine          | 3 weeks  | High        | ✓        |
| 5     | Knowledge Brain        | 3 weeks  | High        | ✓        |
| 6     | AI Orchestrator        | 3 weeks  | High        | ✓        |
| 7     | Agent Framework        | 3 weeks  | High        | ✓        |
| 8     | Coaching Engine        | 2 weeks  | High        | ✓        |
| 9     | Wellness Intelligence  | 2 weeks  | Medium-High | V1       |
| 10    | Voice System           | 3 weeks  | High        | V1       |
| 11    | Mobile App Foundation  | 3 weeks  | Medium      | ✓        |
| 12    | Subscription System    | 2 weeks  | Medium      | ✓        |
| 13    | Analytics & Insights   | 2 weeks  | Medium      | V1       |
| 14    | Security Hardening     | 2 weeks  | High        | ✓        |
| 15    | Production Deployment  | 2 weeks  | Medium-High | ✓        |

**Estimated total duration to MVP**: ~26 weeks (with parallel tracks)
**Estimated total duration to V1**: ~38 weeks

---

---

## Phase 0 — Repository Foundation

### Phase Summary

**Goal**: Establish the monorepo skeleton, CI/CD pipelines, containerised local development environment, shared tooling standards, and documentation home so that every subsequent team can begin work immediately without infrastructure ambiguity.

**Deliverables**:

- Fully initialised TurboRepo/Nx monorepo with top-level folder structure matching `project_structure.md`
- Docker Compose stack running PostgreSQL, Redis, and Qdrant locally
- GitHub Actions pipelines for lint, test, and build
- Branch protection rules, PR templates, and commit-convention enforcement
- `.env.example` template covering all environment variables referenced across all documents
- Root-level `README.md` and `docs/` folder seeded with approved design documents

**Dependencies**: None — this is the starting point.

**Estimated Complexity**: Low

**Estimated Duration**: 1 week

**Acceptance Criteria**:

- `docker compose up` starts all backing services with no manual steps beyond copying `.env.example` to `.env`
- `turbo run lint test build` passes on a clean checkout in under 5 minutes
- GitHub Actions CI runs and passes on a dummy PR
- Every engineer can clone, run, and push a passing PR within 30 minutes of first checkout
- All six approved design documents are committed under `docs/`

---

### Phase 0 Task Breakdown

| Task ID | Description                                                                                                                                                                                                                                                                                                                      | Owner | Dependencies | Effort |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- | ------------ | ------ |
| P0-T01  | Initialise the Git repository; apply TurboRepo workspace configuration; create all top-level folders (`frontend/`, `backend/`, `ai/`, `infra/`, `docs/`, `tests/`, `scripts/`, `shared/`) with `.gitkeep` placeholders and ownership `CODEOWNERS` entries.                                                                       | DO    | —            | S      |
| P0-T02  | Author `docker-compose.yml` defining services for PostgreSQL 16, Redis 7 Cluster-mode, and Qdrant with named volumes, health checks, and port mappings. Validate that all three services start and pass their health checks.                                                                                                     | DO    | P0-T01       | M      |
| P0-T03  | Create `.env.example` documenting every environment variable (database URLs, Redis URI, Qdrant host, LLM API keys, JWT secrets, Stripe keys, ElevenLabs key, embedding model endpoints). Include inline comments explaining each variable.                                                                                       | DO    | P0-T02       | S      |
| P0-T04  | Implement GitHub Actions workflows: `ci.yml` (lint, unit test, build matrix for TypeScript and Python on every PR), `cd.yml` (Docker image build and push to GHCR on merge to `main`), and `release.yml` (semantic-version tagging and changelog generation). Configure branch protection requiring CI passage and one reviewer. | DO    | P0-T01       | M      |
| P0-T05  | Commit all six approved design documents into `docs/`; write root `README.md` covering repo layout, local setup instructions, and links to each doc. Add `PR_TEMPLATE.md` and `CONTRIBUTING.md` with coding standards, branch naming conventions, and the Conventional Commits specification.                                    | DO    | P0-T04       | S      |

---

---

## Phase 1 — Backend Foundation

### Phase Summary

**Goal**: Stand up the FastAPI application skeleton with production-grade configuration management, structured logging, error handling, MongoDB connection pool with Beanie ODM, and a health-check endpoint — giving the backend team a solid, opinionated base to build every feature on top of.

**Deliverables**:

- FastAPI application factory with app settings via Pydantic `BaseSettings`
- MongoDB connection pool via Motor (async driver) with Beanie ODM initialization
- Redis async client wrapper with connection pool
- Qdrant client wrapper (connection pool + helper methods)
- Structured JSON logging via `structlog` with request-ID propagation
- Global exception handler translating Python exceptions into the error envelope defined in `api_contracts.md` §2.3
- `GET /health` endpoint returning service and dependency liveness
- Pytest configuration with MongoDB fixtures using `pytest-asyncio` and a test database

**Dependencies**: Phase 0 complete (Docker Compose stack available)

**Estimated Complexity**: Medium

**Estimated Duration**: 2 weeks

**Acceptance Criteria**:

- `GET /health` returns `200 OK` with status of MongoDB, Redis, and Qdrant dependencies
- Beanie ODM initializes successfully and can perform basic CRUD operations on MongoDB
- All unhandled exceptions return the standard `ErrorResponse` envelope (never a raw Python traceback)
- Test suite runs in isolation against a dedicated test MongoDB database seeded by fixtures
- Structured logs include `request_id`, `user_id` (when authenticated), `duration_ms`, and `status_code` on every request

---

### Phase 1 Task Breakdown

| Task ID | Description                                                                                                                                                                                                                                                                                                                                                                 | Owner    | Dependencies                                                                                                                                                                                                                                                                                | Effort |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ---------------------- | --- |
| P1-T01  | Scaffold the `backend/` Python project: `pyproject.toml`, `requirements.txt` (FastAPI, motor, beanie, Redis, structlog, Pydantic-Settings, httpx, pytest-asyncio). Set up `backend/app/core/config.py` loading all settings from environment with validation.                                                                                                               | BE       | P0-T03                                                                                                                                                                                                                                                                                      | S      |
| P1-T02  | Implement the MongoDB connection pool via Motor and Beanie ODM initialization. Create the base document model classes and establish the connection lifecycle (startup/shutdown). Create initial document collections (empty schema) to verify the ODM pipeline.                                                                                                             | BE       | P1-T01                                                                                                                                                                                                                                                                                      | M      |
| P1-T03  | Build async Redis client wrapper (`backend/app/core/redis.py`) with connection-pool management, typed `get/set/delete/expire` helpers, and graceful reconnection. Build Qdrant client wrapper (`backend/app/core/qdrant.py`) with collection-bootstrap on startup.                                                                                                          | BE       | P1-T01                                                                                                                                                                                                                                                                                      | M      |
| P1-T04  | Implement structured logging middleware (`structlog` + `asgi-correlation-id`): generate a `request_id` UUID per request, attach it to the log context, emit a single JSON log line per request with method, path, status code, and duration. Implement the global exception handler that maps Python exceptions to `ErrorResponse` envelopes per §2.3 of the API contracts. | BE       | P1-T01                                                                                                                                                                                                                                                                                      | M      |
| P1-T05  | Create `GET /v1/health` returning a JSON body with `status: ok                                                                                                                                                                                                                                                                                                              | degraded | down`and a`components` map showing individual health of MongoDB, Redis, and Qdrant. Wire up pytest configuration: shared fixtures for a test MongoDB client, test Redis client, and fresh document collections per test session. Validate that tests can create and roll back transactions. | BE, QA | P1-T02, P1-T03, P1-T04 | M   |

---

---

## Phase 2 — Authentication & Users

### Phase Summary

**Goal**: Implement the complete authentication surface (register, login, logout, token refresh, email verification, password reset, change password) and the User/Profile CRUD layer, establishing the JWT RS256 signing infrastructure and RBAC middleware that all subsequent endpoints will depend on.

**Deliverables**:

- `users` and `profiles` MongoDB collections (Beanie document models)
- All eight `/v1/auth/*` endpoints per §4.1 of the API contracts
- RS256 JWT issuance with 15-minute access tokens and 30-day refresh tokens
- Refresh-token rotation with a Redis deny-list for revoked tokens
- `/v1/users/me` (GET, PATCH, DELETE) and `/v1/profiles/me` (GET, PATCH) per §4.2–4.3
- RBAC `Authorization` middleware that validates scopes on every protected endpoint
- Rate-limiting middleware applying tier-based limits per §2.4
- Email-send integration (transactional email via SendGrid/Resend) for verification and reset flows
- Full Pytest coverage for all auth and user endpoints

**Dependencies**: Phase 1 complete

**Estimated Complexity**: Medium

**Estimated Duration**: 2 weeks

**Acceptance Criteria**:

- Full register → verify email → login → refresh → logout lifecycle works end-to-end
- Access tokens expire at exactly 15 minutes; refresh tokens rotate on every use
- Revoked refresh tokens are rejected within the same second
- Rate limits return `429` with `Retry-After` header when exceeded
- Missing `Idempotency-Key` on register returns `400 VALIDATION_ERROR`
- RBAC rejects a `user`-scoped token accessing an `admin`-only route with `403 UNAUTHORIZED`
- Password stored as Argon2 hash; no plaintext ever logged

---

### Phase 2 Task Breakdown

| Task ID | Description                                                                                                                                                                                                                                                                                                                                                                                 | Owner  | Dependencies   | Effort |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | -------------- | ------ |
| P2-T01  | Create Beanie document models for `users` and `profiles` collections with all fields, indexes, and validation as specified in `database_design.md` §3.1–3.2. Include the `audit_log` document model (§3.15) used by auth events. Initialize the MongoDB collections with proper indexes.                                                                                                    | BE     | P1-T02         | M      |
| P2-T02  | Implement JWT infrastructure: RS256 key-pair generation/storage, `create_access_token` and `create_refresh_token` functions, `decode_token` with audience and issuer validation. Build JWKS endpoint `GET /v1/auth/.well-known/jwks.json`. Implement refresh-token rotation with Redis deny-list for revoked tokens.                                                                        | BE     | P1-T03, P2-T01 | L      |
| P2-T03  | Build all eight `/v1/auth/*` endpoints: `register`, `login`, `logout`, `refresh`, `forgot-password`, `reset-password`, `verify-email`, `change-password`. Each must enforce the validation rules from §4.1, apply the correct per-IP rate limits, and emit the appropriate audit log event. Integrate a transactional email service (SendGrid or Resend) for verification and reset emails. | BE     | P2-T02         | L      |
| P2-T04  | Implement RBAC `Authorization` middleware: extract JWT from `Bearer` header, decode and validate, inject `current_user` into the request state, enforce scope requirements declared on each route via a `require_scope()` dependency. Apply tier-based rate-limiting middleware using Redis token buckets per §2.4.                                                                         | BE     | P2-T02         | M      |
| P2-T05  | Build `/v1/users/me` (GET, PATCH, DELETE) and `/v1/profiles/me` (GET, PATCH) with all request/response schemas, validation rules, and soft-delete logic per §4.2–4.3. Write comprehensive Pytest test suite covering happy paths, validation errors, auth failures, rate limiting, and idempotency key enforcement.                                                                         | BE, QA | P2-T03, P2-T04 | M      |

---

---

## Phase 3 — Conversations & Messages

### Phase Summary

**Goal**: Implement the Conversation and Message domain — the persistent storage layer for all AI-user dialogues — including REST endpoints, cursor-based pagination, soft-delete, and the foundational WebSocket infrastructure that the Coaching Engine will later consume.

**Deliverables**:

- `conversations` and `messages` Alembic migration
- `/v1/conversations` (POST, GET) and `/v1/conversations/{id}` (GET, DELETE) per §4.4.1
- `/v1/messages` (POST, GET) and `/v1/messages/{id}` (GET) per §4.4.2
- Cursor-based pagination utility used by both list endpoints
- WebSocket scaffold at `wss://.../v1/coaching/ws/{sessionId}` accepting connections and echoing heartbeat pings
- Full-text search index on `messages.content` (GIN tsvector) exercised by an optional `?search=` query parameter

**Dependencies**: Phase 2 complete

**Estimated Complexity**: Medium

**Estimated Duration**: 2 weeks

**Acceptance Criteria**:

- Creating a conversation and then posting 50 messages paginate correctly with consistent cursors
- WebSocket connection accepts ping and replies with pong; connection closes cleanly on client disconnect
- Soft-deleting a conversation hides it from list endpoints but preserves the database row with `deleted_at` set
- Full-text search on messages returns results matching the query within 200ms for a 10,000-message dataset
- All endpoints comply with the standard response envelope and error model from §2.1–2.3

---

### Phase 3 Task Breakdown

| Task ID | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Owner                                                                                                                                                    | Dependencies   | Effort                 |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ---------------------- | --- |
| P3-T01  | Write Alembic migration creating `conversations` and `messages` tables with all fields, composite indexes (including the GIN full-text index on `messages.content`), and foreign-key constraints per `database_design.md` §3.3–3.4.                                                                                                                                                                                                                                                             | BE                                                                                                                                                       | P2-T01         | S                      |
| P3-T02  | Implement the cursor-based pagination utility as a reusable SQLAlchemy helper: encode/decode opaque base64 cursors from primary key + sort field; apply `WHERE id > cursor_value` efficiently; return `nextCursor`, `prevCursor`, and `limit` in `meta.pagination` per §2.6.                                                                                                                                                                                                                    | BE                                                                                                                                                       | P1-T02         | M                      |
| P3-T03  | Build `/v1/conversations` (POST, GET) and `/v1/conversations/{id}` (GET, DELETE) with `ConversationCreateRequest`, `ConversationResponse`, `ConversationDetailResponse`, and `ConversationListResponse` Pydantic schemas. Enforce ownership checks (users can only access their own conversations). Apply soft-delete on DELETE.                                                                                                                                                                | BE                                                                                                                                                       | P3-T01, P3-T02 | M                      |
| P3-T04  | Build `/v1/messages` (POST, GET) and `/v1/messages/{id}` (GET) with `MessageCreateRequest` supporting `type: text                                                                                                                                                                                                                                                                                                                                                                               | voice`and`payload`up to 2MB for voice. Enforce`conversationId`ownership. Implement the optional`?search=` query parameter using the GIN full-text index. | BE             | P3-T01, P3-T02, P3-T03 | M   |
| P3-T05  | Implement the WebSocket connection manager (`backend/app/api/coaching.py`): accept `wss://.../v1/coaching/ws/{sessionId}` connections after JWT validation, maintain an in-memory registry of active connections keyed by `sessionId`, handle ping/pong heartbeat every 30 seconds, and broadcast a `heartbeat` event. This is the scaffold that Phase 6 (AI Orchestrator) will plug into. Write QA tests for all REST endpoints including pagination edge cases and voice payload size limits. | BE, QA                                                                                                                                                   | P3-T03, P3-T04 | M                      |

---

---

## Phase 4 — Memory Engine

### Phase Summary

**Goal**: Build the full semantic memory lifecycle — ingestion, chunking, embedding, Qdrant upsert, metadata persistence in PostgreSQL, cache layer in Redis, retrieval with hybrid ANN+BM25, and the Memory REST API — forming the persistent cognitive layer that all AI components depend on.

**Deliverables**:

- `memory` table Alembic migration per `database_design.md` §3.5
- `ai/memory_engine/` module: `chunker.py`, `embedder.py`, `qdrant_client.py`, `schemas.py`, `retention.py`
- Qdrant `user_memory` collection initialised with IVF-PQ index, cosine distance, and 1536-dim vectors
- Embedding pipeline supporting Groq `embed-3-large` (primary) and Gemini `embedding-v2` (secondary)
- Redis cache layer for recently accessed vector metadata (24-hour TTL)
- All five `/v1/memory` endpoints per §4.5 including vector-search via `?vectorSearch=true&query=`
- Background retention worker enforcing TTL policies (episodic 90 days, semantic 180 days)
- Batch embedding optimisation (up to 32 chunks per provider request)

**Dependencies**: Phase 3 complete; Qdrant service running (Phase 0)

**Estimated Complexity**: High

**Estimated Duration**: 3 weeks

**Acceptance Criteria**:

- A 5,000-word journal entry is chunked, embedded, and searchable in Qdrant within 10 seconds
- Vector search returns top-k results ranked by cosine similarity with `relevanceScore` in the response
- Redis cache is populated on first retrieval and served from cache on subsequent requests within 24 hours
- Retention worker deletes vectors older than the TTL without affecting active records
- Provider fallback switches from Groq to Gemini when Groq returns a 5xx error
- Batch embedding processes 32 chunks in a single provider request, not 32 individual requests

---

### Phase 4 Task Breakdown

| Task ID | Description                                                                                                                                                                                                                                                                                                                                                                                                      | Owner      | Dependencies | Effort |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------ | ------ |
| P4-T01  | Write Alembic migration creating the `memory` table per §3.5. Initialise the Qdrant `user_memory` collection with vector size 1536, cosine distance metric, IVF-PQ index (2048 clusters), and replication factor 2. Document the collection schema (`user_id`, `source`, `created_at` payload fields).                                                                                                           | BE, AI     | P3-T01       | S      |
| P4-T02  | Implement `ai/memory_engine/chunker.py`: hybrid sliding-window strategy (1k-token windows with 200-token stride) and semantic breakpoint detection where paragraph boundaries align with topic shifts. Implement `ai/memory_engine/schemas.py`: Pydantic models for `MemoryChunk`, `VectorMetadata`, and `MemoryEntry`.                                                                                          | AI         | P4-T01       | M      |
| P4-T03  | Implement `ai/memory_engine/embedder.py`: provider-agnostic embedding client supporting Groq `embed-3-large` as primary and Gemini `embedding-v2` as fallback. Implement batch queuing (accumulate up to 32 chunks before dispatching a single provider request). On provider 5xx, retry once then switch to the secondary provider.                                                                             | AI         | P4-T02       | M      |
| P4-T04  | Implement `ai/memory_engine/qdrant_client.py`: connection-pool wrapper with `upsert_vectors`, `search_vectors` (returning top-k with score), `delete_vectors`, and `get_vector_by_id` helpers. Implement Redis cache layer in `ai/memory_engine/`: on retrieval, check Redis `vector_meta:{vector_id}` (24h TTL) before querying Qdrant. Populate cache on cache miss.                                           | AI, BE     | P4-T03       | M      |
| P4-T05  | Build all five `/v1/memory` REST endpoints per §4.5: GET (list with type/tag filters), GET `/{id}`, POST (create + trigger async embed pipeline), PATCH (update + re-embed), DELETE (soft-delete + schedule Qdrant deletion). Implement vector-search path: when `?vectorSearch=true&query=<text>`, compute query embedding then call `qdrant_client.search_vectors`, returning `relevanceScore` on each result. | BE, AI     | P4-T04       | L      |
| P4-T06  | Implement `ai/memory_engine/retention.py`: a Celery/Dramatiq periodic task that scans `memory` rows with `created_at` older than the TTL thresholds (episodic 90 days, semantic 180 days), soft-deletes PostgreSQL rows, and purges corresponding Qdrant vectors. Write full QA test suite for all memory endpoints, embedding pipeline, and the retention worker using mocked LLM provider calls.               | AI, BE, QA | P4-T05       | M      |

---

---

## Phase 5 — Knowledge Brain (RAG)

### Phase Summary

**Goal**: Build the Retrieval-Augmented Generation pipeline — document ingestion, chunking, embedding, Qdrant indexing, hybrid ANN+BM25 retrieval with LLM re-ranking, context injection, and the Knowledge Brain REST API — forming the enriched-prompt assembly layer consumed by the AI Orchestrator.

**Deliverables**:

- `ai/knowledge_brain/` module: `provider/groq.py`, `provider/gemini.py`, `prompt_templates/`, `response_parser.py`, `rate_limiter.py`, `cache.py`
- Document ingestion pipeline (PDF via pdftotext/Tesseract, text, notes) with async Celery workers
- `/v1/knowledge/upload`, `/v1/knowledge/documents`, `/v1/knowledge/documents/{id}` per §4.11
- `/v1/rag/query` endpoint with hybrid retrieval (ANN + BM25 re-rank + Haiku re-ranker)
- `/v1/rag/reindex` and `/v1/rag/status` for admin-triggered re-indexing
- Token-budget rate limiter (`rate_limiter.py`) enforcing per-user per-model quotas
- In-memory LRU cache for repeated prompts (`cache.py`)
- `DocumentUploaded` and `RagReindexFinished` events published to the event bus

**Dependencies**: Phase 4 complete

**Estimated Complexity**: High

**Estimated Duration**: 3 weeks

**Acceptance Criteria**:

- A 50MB PDF is uploaded, ingested, chunked, and searchable via `/v1/rag/query` within 60 seconds
- Hybrid retrieval (ANN + BM25) outperforms pure ANN on an internal test set by nDCG@10 ≥ 0.05
- Re-ranking with Claude Haiku reduces irrelevant results in the top-5 by at least 20% versus raw ANN
- Token-budget limiter aborts LLM calls and returns a structured error when a user exceeds their quota
- LRU cache returns a cached response for an identical prompt within 5ms (no provider round-trip)
- `RagReindexFinished` event is published to the event bus within 5 seconds of job completion

---

### Phase 5 Task Breakdown

| Task ID | Description                                                                                                                                                                                                                                                                                                                                                                                                                                      | Owner  | Dependencies   | Effort |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ | -------------- | ------ |
| P5-T01  | Implement `ai/knowledge_brain/provider/groq.py` and `ai/knowledge_brain/provider/gemini.py`: thin async clients wrapping the respective REST APIs for chat completions and embeddings. Both must support streaming responses, configurable timeout, structured error mapping to the internal error envelope, and per-model token counting.                                                                                                       | AI     | P4-T03         | M      |
| P5-T02  | Build the document ingestion pipeline as a Celery async task: accept uploaded files (PDF, TXT, MD), extract text (pdftotext for native PDFs; Tesseract OCR for scanned), detect language, apply the hybrid sliding-window chunker from Phase 4, embed each chunk via the Phase 4 embedder, and upsert into Qdrant. Persist document metadata and ingestion status in PostgreSQL. Publish `DocumentUploaded` event on completion.                 | AI, BE | P5-T01, P4-T04 | L      |
| P5-T03  | Build `/v1/knowledge/upload` (multipart, ≤50MB), `/v1/knowledge/documents` (list with cursor pagination), and `/v1/knowledge/documents/{id}` (GET metadata + optional binary download, DELETE soft-delete) per §4.11. Return `ingestStatusUrl` so the client can poll ingestion progress.                                                                                                                                                        | BE     | P5-T02         | M      |
| P5-T04  | Implement the hybrid retrieval pipeline in `ai/knowledge_brain/`: (1) ANN search on Qdrant (top-200), (2) BM25 re-rank on raw text of the top-200, (3) final re-rank using Claude Haiku over the top-20 to produce a relevance score, (4) personalization boost multiplying the score by user-specific weights from Goal Memory. Return up to `topK` (max 20) source snippets (max 250 chars each) with scores.                                  | AI     | P5-T02, P4-T04 | L      |
| P5-T05  | Build `/v1/rag/query` (POST, per §4.11), `/v1/rag/reindex` (POST, admin-only, returns `taskId`), and `/v1/rag/status` (GET, admin-only). Implement `rate_limiter.py` (per-user per-model token budget tracked in Redis) and `cache.py` (in-memory LRU keyed by prompt hash). Publish `RagReindexFinished` event on job completion.                                                                                                               | BE, AI | P5-T04         | M      |
| P5-T06  | Seed `ai/knowledge_brain/prompt_templates/` with Jinja-style templates for each coaching domain (mental health, productivity, learning, fitness, career, finance, relationships). Implement `response_parser.py` for structured output extraction (JSON schema validation on LLM responses). Write QA test suite covering ingestion pipeline, retrieval quality, rate-limiter enforcement, and all RAG REST endpoints with mocked LLM providers. | AI, QA | P5-T05         | M      |

---

---

## Phase 6 — AI Orchestrator

### Phase Summary

**Goal**: Build the central AI Orchestrator — the single entry point for all AI-driven workflows — including intent classification, context assembly (via the Context Builder), model routing (LLM Router), cost-aware model selection, fallback handling, and the full request lifecycle from WebSocket message to structured LLM response delivered back to the client.

**Deliverables**:

- `ai/agent_system/orchestrator.py`: full request lifecycle per `system_architecture.md` §1
- Intent classification with Claude Haiku (confidence ≥ 0.78 threshold)
- LLM Router implementing the four-branch decision tree from `system_architecture.md` §15 (voice, enterprise, budget, latency)
- Context Builder assembling `{system_prompt, user_prompt, retrieved_chunks, metadata}` from last-5 messages + wellness score + memory chunks + personalization blueprint
- Personalization Engine computing the User Blueprint and caching it in Redis
- Cost tracking: per-request token usage logged to `audit_log`; per-user budget quota enforced via Redis counters
- Failure recovery for LLM timeouts, Qdrant unavailability, and cost overruns per `system_architecture.md` §13
- WebSocket integration: Orchestrator receives messages from the Phase 3 WebSocket scaffold and writes `assistant_message` events back

**Dependencies**: Phases 4 and 5 complete

**Estimated Complexity**: High

**Estimated Duration**: 3 weeks

**Acceptance Criteria**:

- A coaching utterance travels from WebSocket → Orchestrator → Context Builder → LLM Router → LLM → WebSocket response in under 2 seconds (p95, non-voice path)
- Intent classification correctly routes ≥ 90% of a 500-request evaluation set to the right primary agent
- LLM Router selects Groq for voice-flagged and budget-constrained requests; Gemini for enterprise-tier users
- When Groq times out, the fallback to Gemini occurs within 500ms and the user receives a valid response
- When a user's token budget is exhausted, subsequent requests return a structured error with a human-readable message, not a raw exception
- All token consumption is written to `audit_log` within the same database transaction as the response

---

### Phase 6 Task Breakdown

| Task ID | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Owner  | Dependencies           | Effort |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ---------------------- | ------ |
| P6-T01  | Implement intent classification in `ai/agent_system/orchestrator.py`: call Claude Haiku with the user utterance and a system prompt containing the six intent labels (`goal_update`, `recommendation`, `crisis_escalation`, `knowledge_query`, `tool_action`, `feedback`). If confidence < 0.78, fall back to `general-assistant`. Cache classification result in Redis for 60 seconds to avoid duplicate calls for the same session message.                             | AI     | P5-T01                 | M      |
| P6-T02  | Build the LLM Router (`backend/app/ai/llm_router.py`): implement the four-branch decision tree — (1) voice-related → Groq, (2) enterprise tier → Gemini, (3) token budget OK + latency < 300ms → Groq, else → Gemini. Pull real-time token pricing from a configurable table. Implement fallback: if primary model returns 5xx or times out within `model_timeout_ms`, switch to the other provider; if both fail, return the generic degraded-service response.          | AI, BE | P5-T01, P6-T01         | M      |
| P6-T03  | Build the Context Builder (`backend/app/ai/context_builder.py`): assemble the `{system_prompt, user_prompt, retrieved_chunks, metadata}` JSON payload by (1) querying last 5 messages from PostgreSQL, (2) reading current wellness score from Redis cache, (3) fetching top-k memory chunks via the Memory Engine, (4) fetching RAG chunks via the Knowledge Brain, (5) applying the Personalization Blueprint. Enforce total token budget by trimming retrieved chunks. | AI, BE | P4-T05, P5-T04, P6-T02 | L      |
| P6-T04  | Implement the Personalization Engine (`backend/app/ai/personalization.py`): analyse goal completion rates, habit adherence, and interaction sentiment from PostgreSQL; produce a `UserBlueprint` with `tone`, `depth`, and `domains` flags; store in `users.personalization` (PostgreSQL) and cache in Redis with a 1-hour TTL. Expose a background refresh triggered by `HabitCompleted` and `GoalUpdated` events.                                                       | AI, BE | P6-T03                 | M      |
| P6-T05  | Wire the Orchestrator end-to-end: receive a message from the Phase 3 WebSocket scaffold, pass it through intent classification → context building → LLM routing → provider call → response parsing. Write the `assistant_message` event back over the WebSocket. Log token usage to `audit_log`. Enforce per-user token budget via Redis counter; when exceeded, publish a `BUDGET_EXCEEDED` structured error message over the WebSocket.                                 | AI, BE | P6-T03, P6-T04         | L      |
| P6-T06  | Implement the failure recovery matrix from `system_architecture.md` §13: LLM timeout handling with provider fallback; Qdrant unavailability with Redis-cached vectors fallback; Redis miss with PostgreSQL reload; cost-overrun abort; background-worker crash detection via Redis heartbeat keys. Write QA integration tests covering all failure scenarios by injecting simulated provider failures.                                                                    | BE, QA | P6-T05                 | M      |

---

---

## Phase 7 — Agent Framework

### Phase Summary

**Goal**: Build the composable multi-agent system — the Agent Registry, Executor, and the seven specialized domain agents (Life Strategist, Mental Wellness, Learning, Fitness, Career, Finance, Relationship) — each running as a stateless worker, collaborating via the Fusion Engine, with safety guardrails applied on every response.

**Deliverables**:

- `ai/agent_system/agent_registry.py`: catalog of all agents with JSON-Schema `input`/`output` contracts
- `ai/agent_system/executor.py`: parallel and sequential agent invocation with confidence scores and action suggestions
- `ai/agent_system/hooks/`: pre-run (safety input scan) and post-run (toxicity filter, length truncation, markdown sanitisation) hooks
- Seven domain agent implementations as stateless Python callables, each with its own Jinja prompt template
- Fusion Engine: rule-based priority matrix that merges multi-agent suggestions (Mental Wellness > Finance for crisis)
- Safety Layer: prompt injection detection, toxicity detection (Perspective API), crisis escalation protocol, mental-health and financial-advice guardrails
- A/B testing scaffold for prompt versions (`prompt_version_id` tracking)
- `CoachingCompleted` event published to the event bus at session end

**Dependencies**: Phase 6 complete

**Estimated Complexity**: High

**Estimated Duration**: 3 weeks

**Acceptance Criteria**:

- All seven agents return structured JSON responses matching their declared output schema 100% of the time
- Parallel invocation of all seven agents completes within 3 seconds (p95)
- Crisis escalation triggers within one response turn when sentiment < -0.8 and crisis keywords are present
- The Fusion Engine correctly elevates the Mental Wellness agent response in 100% of simulated crisis test cases
- Prompt injection attempts (e.g., "ignore previous instructions") are intercepted and logged without producing unsafe output
- The A/B testing scaffold assigns traffic to two prompt versions and records per-version `user_satisfaction` and `goal_completion_impact` metrics

---

### Phase 7 Task Breakdown

| Task ID | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Owner      | Dependencies | Effort |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------ | ------ |
| P7-T01  | Implement `ai/agent_system/agent_registry.py`: define the catalog of all seven domain agents, each with a unique `agent_id`, `description`, `input_schema` (JSON Schema), `output_schema`, `primary_data_sources`, and `prompt_template_path`. Implement `ai/agent_system/executor.py`: accepts a list of agent IDs and a context payload, invokes them concurrently via `asyncio.gather`, collects confidence scores and action suggestions, handles per-agent timeout and fallback.                                                                                                                                            | AI         | P6-T05       | M      |
| P7-T02  | Implement the seven domain agent callables (one Python module per agent under `ai/agent_system/agents/`): Life Strategist, Mental Wellness, Learning, Fitness, Career, Finance, and Relationship. Each agent loads its Jinja prompt template, fills in `{user_goals}`, `{recent_events}`, `{retrieved_chunks}` placeholders, calls the LLM Router, and returns a validated structured response matching its output schema.                                                                                                                                                                                                       | AI         | P7-T01       | L      |
| P7-T03  | Build the Fusion Engine (`ai/agent_system/fusion.py`): accept the list of agent responses with confidence scores, apply the rule-based priority matrix (Mental Wellness > Finance > Life Strategist > others for crisis scenarios), merge non-conflicting action suggestions, and produce a single synthesized response with provenance links to the contributing memory chunks.                                                                                                                                                                                                                                                 | AI         | P7-T02       | M      |
| P7-T04  | Implement the Safety Layer (`ai/agent_system/safety.py`): (1) input scan — regex + Haiku classifier for prompt injection; (2) output scan — Perspective API toxicity scorer (threshold 0.7); (3) crisis escalation — if sentiment < -0.8 AND crisis keywords present, override agent response with emergency resources and log to compliance channel; (4) financial-advice guardrail — cap actionable investment suggestions to ≤5% of session output; (5) medical-diagnosis guardrail — deterministic rule set rejecting diagnostic claims.                                                                                     | AI, BE     | P7-T03       | M      |
| P7-T05  | Implement pre-run and post-run hooks (`ai/agent_system/hooks/`): pre-run applies the Safety Layer input scan and injects personalization overrides; post-run applies toxicity filtering, length truncation (max 2,000 characters), and Markdown sanitisation. Implement the A/B testing scaffold: assign `prompt_version_id` per request (5% traffic slice), record `user_satisfaction` and `goal_completion_impact` against each version in PostgreSQL. Publish `CoachingCompleted` event to the event bus at session end. Write QA tests for all seven agents, the Fusion Engine, each safety guardrail, and the A/B scaffold. | AI, BE, QA | P7-T04       | M      |

---

---

## Phase 8 — Coaching Engine

### Phase Summary

**Goal**: Implement the structured AI coaching layer — the four coaching modes (assessment, nudge, reflection, escalation), the Proactive Nudger background worker, the end-day reflection loop, and all `/v1/coaching/*` REST and WebSocket endpoints — delivering the core user-facing intelligence of Lumenly.

**Deliverables**:

- `coaching_sessions` Alembic migration (§3.12)
- `/v1/coaching/session` (POST), `/v1/coaching/history` (GET), `/v1/coaching/insights` (GET) per §4.10
- Four coaching session types: `assessment`, `nudge`, `reflection`, `escalation`
- Initial 30-minute assessment flow that bootstraps the User Blueprint and baseline scores
- Proactive Nudger: background Celery worker sending context-aware nudges based on missed habits, wellness dips, and upcoming deadlines
- End-day reflection loop: nightly analysis of journal sentiment trends and action recommendations
- Full WebSocket session lifecycle: `assistant_message`, `tool_call`, `tool_response`, `error`, `heartbeat` message types per §4.19.1
- `ai_insights` Alembic migration (§3.13) and persistence of coaching-derived insights

**Dependencies**: Phases 6 and 7 complete

**Estimated Complexity**: High

**Estimated Duration**: 2 weeks

**Acceptance Criteria**:

- An assessment session produces a complete `UserBlueprint` stored in PostgreSQL within the 30-minute flow
- A nudge is delivered within 60 seconds of a missed habit check-in being recorded
- The end-day reflection loop runs every night at the user's local midnight (using `profile.time_zone`)
- WebSocket sessions support all five message types; `tool_call` with no client response within 5 seconds triggers the fallback response
- `GET /v1/coaching/insights` returns at least one insight per active coaching domain for a user with 7+ days of data

---

### Phase 8 Task Breakdown

| Task ID | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Owner  | Dependencies   | Effort |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | -------------- | ------ |
| P8-T01  | Write Alembic migrations creating `coaching_sessions` (§3.12) and `ai_insights` (§3.13) tables with all fields and indexes. Implement Pydantic request/response schemas for all coaching endpoints: `CoachingSessionRequest`, `CoachingSessionResponse`, `CoachingHistoryResponse`, `CoachingInsightsResponse`.                                                                                                                                                              | BE     | P3-T01         | S      |
| P8-T02  | Build `/v1/coaching/session` (POST): validate agent enum and `contextIds`, create a `coaching_sessions` row with `session_type`, generate a `sessionId`, return the WebSocket URL. Wire the Orchestrator to the coaching session: when a WebSocket connection opens for the session, load the coaching session context and begin the appropriate agent flow. Implement all five WebSocket message types per §4.19.1 including the 5-second `tool_call` timeout and fallback. | BE, AI | P7-T05, P8-T01 | L      |
| P8-T03  | Implement the four coaching session type flows: (1) `assessment` — 30-minute structured interview across all pillars, bootstraps `UserBlueprint`; (2) `nudge` — short context-aware prompt generated from habit/goal/wellness state; (3) `reflection` — end-day journal sentiment analysis and action recommendations; (4) `escalation` — crisis-detected flow that surfaces professional resources and logs to the compliance channel.                                      | AI     | P8-T02         | L      |
| P8-T04  | Build the Proactive Nudger Celery worker: runs every 15 minutes, queries users with missed habits, wellness score drops, or upcoming goal deadlines, generates a personalised nudge via the Nudge agent, and delivers it as a push notification (APNs/FCM stub for MVP) or in-app message (write to `messages` table).                                                                                                                                                       | BE, AI | P8-T03         | M      |
| P8-T05  | Build `/v1/coaching/history` (GET with cursor pagination) and `/v1/coaching/insights` (GET). Persist coaching-derived insights to `ai_insights` at session end. Write QA test suite for all coaching REST endpoints, the assessment flow (stubbed LLM), the nudger worker timing, and WebSocket session lifecycle.                                                                                                                                                           | BE, QA | P8-T04         | M      |

---

---

## Phase 9 — Wellness Intelligence Engine

### Phase Summary

**Goal**: Build the Wellness Intelligence Engine — sensor data ingestion, rolling analytics workers, mood and journal data aggregation, stress forecasting, and the `/v1/wellness/*` endpoints — providing the real-time health signal layer that feeds the Context Builder and Proactive Nudger.

**Deliverables**:

- `mood_tracking` and `wellness_intelligence` Alembic migrations (§3.7)
- FastAPI sensor ingestion endpoint writing to Redis streams
- Celery analytics workers consuming Redis streams and computing rolling averages, stress forecasts, and per-pillar wellness scores
- All four `/v1/wellness/*` endpoints (dashboard, score, trends, recommendations) per §4.12
- All five `/v1/moods/*` endpoints per §4.7
- Wellness score written to Redis cache (10-minute TTL) for instant Context Builder access
- Prometheus metrics: `wellness_ingestion_rate`, `analytics_worker_lag`, `wellness_score_p95`

**Dependencies**: Phase 3 complete; Phase 8 recommended (Proactive Nudger consumes wellness score)

**Estimated Complexity**: Medium-High

**Estimated Duration**: 2 weeks

**Acceptance Criteria**:

- A sensor payload submitted to the ingestion endpoint appears as a computed wellness score in Redis within 30 seconds
- Wellness score is available via `GET /v1/wellness/score` with a cache hit (< 5ms) within the 10-minute TTL window
- Trends endpoint returns correct 7-day and 30-day aggregates for a test user with 60 days of mood data
- Analytics worker lag (measured via Prometheus) stays below 60 seconds under a load of 1,000 concurrent sensor streams
- Stress forecast for the next 24 hours is included in `GET /v1/wellness/recommendations` for users with ≥ 7 days of data

---

### Phase 9 Task Breakdown

| Task ID | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Owner                                                 | Dependencies   | Effort |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- | -------------- | ------ | --- |
| P9-T01  | Write Alembic migration creating `mood_tracking` and a `wellness_intelligence` summary table. Implement the FastAPI sensor ingestion endpoint (`POST /v1/internal/wellness/ingest`): accept sensor payloads (heart rate, sleep score, activity), validate schema, write to a Redis Stream (`wellness_stream:{user_id}`).                                                                                                                                                           | BE                                                    | P3-T01         | S      |
| P9-T02  | Implement Celery analytics workers: (1) a stream consumer that reads from `wellness_stream:{user_id}`, computes rolling averages (7-day, 30-day) for energy, stress, and activity, persists aggregates to `wellness_intelligence` in PostgreSQL, and writes the current wellness score to Redis (`wellness_score:{user_id}`, 10-minute TTL); (2) a stress-forecast worker that applies a simple exponential-smoothing model on 7-day stress history to produce a 24-hour forecast. | BE, AI                                                | P9-T01         | M      |
| P9-T03  | Build all five `/v1/moods` endpoints (POST, GET list, GET trends per §4.7). Mood entries are written to PostgreSQL `mood_tracking`; the trends endpoint aggregates by `period=7d                                                                                                                                                                                                                                                                                                   | 30d` using a single PostgreSQL window-function query. | BE             | P9-T01 | M   |
| P9-T04  | Build all four `/v1/wellness` endpoints (dashboard, score, trends, recommendations per §4.12). The dashboard aggregates mood, sleep, activity, and goal progress into a single response. The recommendations endpoint calls the Life Strategist and Mental Wellness agents with the current wellness context to generate personalised nudges.                                                                                                                                      | BE, AI                                                | P9-T02, P9-T03 | M      |
| P9-T05  | Add Prometheus metrics for the Wellness Engine (`wellness_ingestion_rate`, `analytics_worker_lag`, `wellness_score_p95`). Wire analytics worker crash recovery: Supervisor restarts the worker; on restart, the worker replays events from the Redis Stream starting from the last acknowledged offset. Write QA tests for ingestion, all REST endpoints, analytics worker timing, and the crash-recovery replay.                                                                  | BE, DO, QA                                            | P9-T04         | M      |

---

---

## Phase 10 — Voice System

### Phase Summary

**Goal**: Implement the complete voice pipeline — speech-to-text transcription, text-to-speech synthesis via ElevenLabs, real-time streaming voice chat over WebSocket, audio caching in Redis, and all `/v1/voice/*` REST and WebSocket endpoints — enabling the "Lumen" voice persona.

**Deliverables**:

- `ai/voice/` module: ElevenLabs TTS and STT clients, audio streaming, caching
- `POST /v1/voice/transcribe` (multipart audio → text) per §4.13
- `POST /v1/voice/synthesize` (text → signed audio URL) per §4.13
- `POST /v1/voice/chat` (bidirectional voice session bootstrap) per §4.13
- Voice WebSocket at `wss://.../v1/voice/ws/{sessionId}` with `audio_in`, `audio_out`, `assistant_text`, `error`, `heartbeat` message types per §4.19.2
- Redis audio blob cache (5-minute TTL) returning signed URLs
- Groq fast-path routing for all voice-flagged requests (< 500ms latency target)
- Voice-to-Orchestrator pipeline: transcribed text fed into the coaching Orchestrator, response synthesised and returned as `audio_out`

**Dependencies**: Phase 6 complete (Orchestrator); ElevenLabs API key configured

**Estimated Complexity**: High

**Estimated Duration**: 3 weeks

**Acceptance Criteria**:

- End-to-end voice round-trip (user speaks → transcribe → Orchestrator → synthesise → audio_out) completes in under 2 seconds (p95) on a stable connection
- Audio chunks ≤ 1MB are accepted; larger chunks return `400 VALIDATION_ERROR`
- Voice WebSocket sends a heartbeat `ping` every 30 seconds; client disconnection is detected and the session is cleaned up within 35 seconds
- Redis audio cache is populated on first TTS synthesis; subsequent identical-text requests are served from cache without an ElevenLabs round-trip
- ElevenLabs HTTP 5xx triggers text-only fallback: response is delivered as an `assistant_text` message over the WebSocket with no audio

---

### Phase 10 Task Breakdown

| Task ID | Description                                                                                                                                                                                                                                                                                                                                                                                                                    | Owner      | Dependencies    | Effort |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | --------------- | ------ |
| P10-T01 | Implement `ai/voice/elevenlabs.py`: async client wrapping ElevenLabs TTS (text → MP3) and STT (audio → text) APIs. Implement connection timeout, retry (once), and structured error mapping. Support configurable voice name and style enum. Implement audio chunk streaming to avoid buffering full MP3 in memory.                                                                                                            | AI         | P0-T03          | M      |
| P10-T02 | Implement `ai/voice/cache.py`: after TTS synthesis, store the MP3 blob in Redis with a 5-minute TTL keyed by a hash of `(text, voice_name, style)`. On TTS requests, check cache first; return a signed URL (pre-signed Redis URL or a temporary `/v1/voice/audio/{token}` endpoint) without calling ElevenLabs.                                                                                                               | AI, BE     | P10-T01         | M      |
| P10-T03 | Build `POST /v1/voice/transcribe` (multipart audio ≤ 5MB, WAV or MP3, language enum → text response), `POST /v1/voice/synthesize` (text ≤ 2KB → audioUrl + durationMs), and `POST /v1/voice/chat` (bootstrap voice session → WebSocket URL) per §4.13. Apply 30 req/min and 20 req/min rate limits respectively.                                                                                                               | BE, AI     | P10-T02         | M      |
| P10-T04 | Implement the Voice WebSocket at `wss://.../v1/voice/ws/{sessionId}`: handle `audio_in` messages (base64 ≤ 1MB), pipe through ElevenLabs STT, forward transcript to the Coaching Orchestrator, pipe the text response through ElevenLabs TTS, return `audio_out` messages. Handle `assistant_text` fallback when TTS fails. Enforce 10 messages/second rate limit (burst ≤ 20). Send heartbeat `ping` every 30 seconds.        | BE, AI     | P10-T03, P6-T05 | L      |
| P10-T05 | Implement the voice fast-path in the LLM Router: any request flagged as `voice_related` by the Orchestrator routes to Groq with the sub-500ms latency profile. Verify that the LLM Router flag propagates correctly from voice WebSocket sessions. Write QA tests for transcription, synthesis (with Redis cache hit/miss), the voice WebSocket lifecycle (including ElevenLabs failure fallback), and rate-limit enforcement. | AI, BE, QA | P10-T04         | M      |

---

---

## Phase 11 — Mobile App Foundation

### Phase Summary

**Goal**: Build the React Native / Expo mobile application skeleton covering navigation, authentication flows, the unified dashboard screen, goals and habits screens, journal entry, AI chat interface, and the service layer wiring the mobile app to the backend API — establishing the complete user-facing surface for MVP.

**Deliverables**:

- `frontend/` Expo project with TypeScript, React Navigation, Zustand store, and Axios service layer
- Auth screens: Register, Login, Verify Email, Forgot Password
- Onboarding flow (5-pillar domain selection, initial assessment prompt)
- Unified Dashboard screen: wellness score widget, goal progress cards, habit streak indicators, daily AI nudge
- Goals screen: list, create (SMART goal form), detail with progress chart
- Habits screen: list, create, daily check-in
- Journal screen: create entry (markdown), list with date filter
- AI Coach screen: text chat interface connected to the coaching WebSocket
- Mood tracking bottom sheet (quick 1–10 slider + emoji picker)
- Design system: theme tokens, shared components (Button, Card, Avatar, ProgressRing, BottomSheet)

**Dependencies**: Phases 2, 3, 8 backend endpoints available; Phase 0 monorepo scaffold

**Estimated Complexity**: Medium

**Estimated Duration**: 3 weeks

**Acceptance Criteria**:

- Complete auth flow (register → verify → login → home) works on iOS Simulator and Android Emulator without manual steps
- Dashboard loads within 1.5 seconds on a cold launch (React Native bundle + first API call)
- AI Coach screen sends a text message and receives a streaming assistant response over the WebSocket
- Habits check-in updates the streak counter on the Dashboard without a full screen reload
- All screens pass accessibility audit (minimum contrast ratio 4.5:1, all interactive elements have accessibility labels)
- TypeScript strict mode enabled; zero type errors in CI

---

### Phase 11 Task Breakdown

| Task ID | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Owner  | Dependencies             | Effort |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ------------------------ | ------ |
| P11-T01 | Scaffold the Expo project with TypeScript, ESLint + Prettier, React Navigation (stack + bottom tabs), Zustand stores (`authStore`, `profileStore`, `goalsStore`, `habitsStore`, `conversationStore`), Axios service layer (`frontend/src/services/`) with auth-token interceptor and 401 auto-refresh logic, and the design system foundation (`frontend/src/theme/`): color tokens, typography scale, spacing, and shared primitive components (Button, Card, Avatar).             | FE     | P0-T01                   | M      |
| P11-T02 | Build authentication screens (Register, Login, Verify Email, Forgot/Reset Password) wired to `/v1/auth/*` endpoints. Implement secure token storage (Expo SecureStore). Build the onboarding flow: pillar domain selection (5 of 10), profile completion, and the initial assessment prompt that opens a coaching WebSocket session.                                                                                                                                                | FE     | P11-T01, P2-T05          | L      |
| P11-T03 | Build the Unified Dashboard screen: fetch wellness score, goal progress summaries, habit streak indicators, and the latest AI nudge in parallel using `Promise.all`; render with skeleton loaders while data loads; add pull-to-refresh. Build the Mood Tracking bottom sheet (1–10 slider + emoji picker) wired to `POST /v1/moods`.                                                                                                                                               | FE     | P11-T01, P9-T04          | M      |
| P11-T04 | Build Goals screens (list with filter chips, create with SMART goal form and date picker, detail with `recharts` progress line chart) wired to `/v1/goals/*` endpoints. Build Habits screens (list with streak display, create form with frequency and reminder time, daily check-in button) wired to `/v1/habits/*` and `POST /v1/habits/{id}/check-in`. Build Journal screens (create entry with Markdown preview, date-filtered list) wired to `/v1/journal/*` endpoints.        | FE     | P11-T01, P3-T01          | L      |
| P11-T05 | Build the AI Coach screen: establish the coaching WebSocket connection on mount, display a chat bubble list with assistant and user messages, support streaming text responses (append characters as they arrive), show typing indicator during LLM generation. Integrate the Mood entry bottom sheet as a floating action. Write Detox E2E tests for the auth flow and the send-a-message coaching flow. Write Jest unit tests for all Zustand stores and service-layer functions. | FE, QA | P11-T02, P11-T04, P8-T02 | L      |

---

---

## Phase 12 — Subscription System

### Phase Summary

**Goal**: Implement the complete SaaS billing layer — Stripe integration for Free, Pro, Team, and Enterprise plans, plan-based feature gating enforced in the API middleware, subscription lifecycle management (upgrade, cancel, past-due), and Stripe webhook handling.

**Deliverables**:

- `subscriptions` Alembic migration (§3.14)
- Stripe customer creation on user registration
- `/v1/subscription` (GET), `/v1/subscription/upgrade` (POST, idempotent), `/v1/subscription/cancel` (POST) per §4.16
- `/v1/webhooks/stripe` handler for `checkout.session.completed`, `invoice.payment_succeeded`, `invoice.payment_failed`, `customer.subscription.deleted`
- Plan-based feature gate middleware: block Free-tier users from voice, financial advisor, and expanded memory endpoints
- `SubscriptionChanged` event published to the event bus
- Admin endpoint `GET /v1/admin/users` filter by plan

**Dependencies**: Phase 2 complete; Stripe account and API keys configured

**Estimated Complexity**: Medium

**Estimated Duration**: 2 weeks

**Acceptance Criteria**:

- Upgrading from Free to Pro via `POST /v1/subscription/upgrade` creates a Stripe subscription and updates the local plan within 5 seconds
- The Stripe webhook verifies the `Stripe-Signature` header; invalid signatures return `401` without processing the payload
- A Free-tier user hitting `/v1/voice/synthesize` receives `403 UNAUTHORIZED` with a plan-upgrade prompt in the error details
- A canceled subscription retains Pro access until `effectiveDate` then downgrades automatically via the `customer.subscription.deleted` webhook
- Idempotency-Key on upgrade prevents duplicate Stripe subscriptions if the request is retried

---

### Phase 12 Task Breakdown

| Task ID | Description                                                                                                                                                                                                                                                                                                                                                                                                                       | Owner      | Dependencies     | Effort |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------------- | ------ |
| P12-T01 | Write Alembic migration creating the `subscriptions` table (§3.14). Add Stripe customer creation to the user registration flow: on `UserCreated` event, call `stripe.customers.create` and store `provider_customer_id` in `subscriptions`. Seed initial `free` plan subscription row.                                                                                                                                            | BE         | P2-T01           | S      |
| P12-T02 | Build `GET /v1/subscription`, `POST /v1/subscription/upgrade` (idempotent via `Idempotency-Key`, creates Stripe checkout session or subscription), and `POST /v1/subscription/cancel` (marks cancellation with `effectiveDate = current period end`) per §4.16.                                                                                                                                                                   | BE         | P12-T01          | M      |
| P12-T03 | Implement `POST /v1/webhooks/stripe`: verify `Stripe-Signature`, deserialise event, handle `checkout.session.completed` (activate subscription), `invoice.payment_succeeded` (renew), `invoice.payment_failed` (set `past_due`, send downgrade warning email), `customer.subscription.deleted` (downgrade to Free). Publish `SubscriptionChanged` event to the event bus on every plan change. Respond `200 OK` within 2 seconds. | BE         | P12-T02          | M      |
| P12-T04 | Implement the plan-based feature gate as a reusable FastAPI dependency (`require_plan(minimum_plan)`): checks `current_user.subscription.plan` against the required minimum; returns `403 UNAUTHORIZED` with a human-readable upgrade prompt if below the threshold. Apply `require_plan("pro")` to voice, financial advisor, and expanded memory endpoints; `require_plan("team")` to admin console endpoints.                   | BE         | P12-T02          | M      |
| P12-T05 | Build the mobile Subscription screen: display current plan, renewal date, usage limits, and an upgrade CTA linking to a Stripe-hosted checkout page (via `expo-web-browser`). Wire up the `SubscriptionChanged` event to update the Zustand `profileStore` via the WebSocket event stream. Write QA tests for the upgrade/cancel lifecycle, webhook signature validation, and feature gate enforcement.                           | FE, BE, QA | P12-T03, P12-T04 | M      |

---

---

## Phase 13 — Analytics & Insights

### Phase Summary

**Goal**: Build the AI Insights generation pipeline — daily, weekly, and monthly insight generation workers, the AI Insights REST API, the admin analytics console endpoints, and the internal Prometheus/Grafana observability stack — providing both user-facing intelligence and operator-level visibility.

**Deliverables**:

- Daily insight Celery worker: generates per-pillar AI insights from coaching, mood, goal, and habit data
- Weekly and monthly aggregation workers with trend detection
- `/v1/insights`, `/v1/insights/daily`, `/v1/insights/weekly`, `/v1/insights/monthly` per §4.14
- `GET /v1/admin/analytics` with metric aggregations (active users, API usage, error rates) per §4.17
- Prometheus metrics published for all AI components: `model_calls`, `tokens_used`, `embedding_calls`, `coaching_sessions_total`, `insight_generation_latency`
- Grafana dashboard configuration for the engineering team
- Evaluation framework metrics: Memory Recall Accuracy, Retrieval Precision, Hallucination Rate trackers from `ai_system_design.md`

**Dependencies**: Phases 8 and 9 complete

**Estimated Complexity**: Medium

**Estimated Duration**: 2 weeks

**Acceptance Criteria**:

- Daily insight worker runs within 30 minutes of midnight in each user's timezone
- `GET /v1/insights/daily` returns at least one insight per active domain for a user with 7+ days of history
- Admin analytics endpoint returns `api_requests_total` and `api_errors_total` grouped by endpoint and date range
- Prometheus scrape endpoint returns all defined metrics within 5 seconds
- Hallucination Rate tracker flags at least 80% of responses that contain factual claims unsupported by retrieved source documents (measured on internal evaluation set)

---

### Phase 13 Task Breakdown

| Task ID | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Owner  | Dependencies   | Effort |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ | -------------- | ------ |
| P13-T01 | Implement the daily insight generation Celery worker: for each user with activity in the last 7 days, aggregate mood, habit, goal, and coaching data, call the Life Strategist agent to generate `wellness_score`, `goal_suggestion`, and `habit_recommendation` insight types, persist to `ai_insights` with a 24-hour `expires_at`. Schedule via Celery Beat to run at 00:05 in each user's local timezone.                                                            | AI, BE | P8-T05, P9-T05 | M      |
| P13-T02 | Implement weekly and monthly aggregation workers: weekly worker computes 7-day KPI shifts (mood trend, habit streak, goal velocity) and generates trend insights; monthly worker produces a "life-report card" summary across all active pillars. Both workers write to `ai_insights` and respect the retention policy (12-month active retention per §3.17).                                                                                                            | AI, BE | P13-T01        | M      |
| P13-T03 | Build all four `/v1/insights` endpoints per §4.14: catalog (GET all insight types), daily, weekly, monthly. Each list endpoint applies cursor pagination, respects `expires_at` filters, and returns the standard response envelope with `generatedAt` timestamp. Build `GET /v1/admin/analytics` supporting `metric`, `range`, and `groupBy` query parameters backed by PostgreSQL aggregate queries and Redis-cached pre-computed summaries.                           | BE     | P13-T02        | M      |
| P13-T04 | Implement Prometheus instrumentation across all AI components: `model_calls_total{model,provider}`, `tokens_used_total{model,user_tier}`, `embedding_calls_total`, `coaching_sessions_total{session_type}`, `insight_generation_latency_seconds`. Expose `/metrics` endpoint. Configure Grafana dashboards for the four key operational views: LLM usage, coaching throughput, wellness analytics, and error rates.                                                      | DO, AI | P6-T06, P9-T05 | M      |
| P13-T05 | Implement the Evaluation Framework trackers from `ai_system_design.md`: (1) Memory Recall Accuracy logged as a ratio of relevant retrieved chunks per request; (2) Retrieval Precision computed as nDCG@10 on a daily batch test set; (3) Hallucination Rate via a self-verification agent (Haiku) that checks each generated claim against retrieved sources. Write QA tests for all insight endpoints, the admin analytics endpoint, and the Prometheus metric scrape. | AI, QA | P13-T04        | M      |

---

---

## Phase 14 — Security Hardening

### Phase Summary

**Goal**: Systematically apply all security controls required for MVP launch and SOC 2 Type II readiness: encryption-at-rest for all PII, GDPR-compliant data deletion, audit log completeness, penetration-testing remediations, dependency vulnerability scanning, CSP and CORS configuration, and security regression tests that run on every CI push.

**Deliverables**:

- AES-256-GCM encryption-at-rest for all `users`, `profiles`, `journal_entries`, `messages`, and `coaching_sessions` text fields via application-level encryption (AWS KMS key management)
- GDPR `/forget` endpoint: soft-delete all user data across PostgreSQL and trigger Qdrant vector purge within 24 hours
- PII tokenisation in the Qdrant vector payload (replace `user_id` with a deterministic hash)
- Dependency vulnerability scanning (Snyk) integrated into the CI pipeline; builds fail on HIGH or CRITICAL CVEs
- CSP headers, CORS whitelist (mobile app origins only), and HSTS enforced via Nginx
- Comprehensive audit log coverage: every write operation on `users`, `goals`, `habits`, `conversations`, `subscriptions` emits an `audit_log` entry
- Security regression test suite (OWASP ZAP scan, SQL-injection payloads, JWT manipulation attempts)

**Dependencies**: All feature phases (1–13) complete

**Estimated Complexity**: High

**Estimated Duration**: 2 weeks

**Acceptance Criteria**:

- No HIGH or CRITICAL CVEs in production dependencies (Snyk scan passes in CI)
- Submitting a GDPR deletion request purges all associated PII from PostgreSQL, Redis, and Qdrant within 24 hours (verified by a QA test that inspects all three stores)
- JWT manipulation (algorithm confusion attack `alg: none`, expired token reuse) is rejected with `401`
- SQL injection payloads in all string input fields return `400 VALIDATION_ERROR`, never a database error
- CSP headers block inline scripts; CORS rejects requests from non-whitelisted origins
- OWASP ZAP scan of the staging environment returns zero HIGH-severity findings

---

### Phase 14 Task Breakdown

| Task ID | Description                                                                                                                                                                                                                                                                                                                                                                                                                          | Owner  | Dependencies | Effort |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ | ------------ | ------ |
| P14-T01 | Implement application-level AES-256-GCM encryption for sensitive text fields (`email`, `content`, `body`, `ai_prompt`, `ai_response`) using an AWS KMS-managed data-encryption key. Build encryption/decryption helpers that are transparent to the SQLAlchemy model layer via custom TypeDecorators. Implement PII tokenisation for Qdrant vector payloads: replace `user_id` with a deterministic HMAC hash before upsert.         | BE     | P5-T02       | L      |
| P14-T02 | Implement the GDPR Data Deletion Worker: triggered by `DELETE /v1/users/me` or a direct admin action, it (1) sets `deleted_at` on all user-owned rows across all tables, (2) purges the user's Qdrant vectors, (3) invalidates all Redis keys for the user, (4) emits a `UserDeleted` audit event. Guarantee completion within 24 hours with a background retry mechanism.                                                           | BE     | P14-T01      | M      |
| P14-T03 | Integrate Snyk into the GitHub Actions CI pipeline: scan Python (`requirements.txt`) and npm (`package.json`) dependencies on every push; fail the build on HIGH or CRITICAL severity CVEs; generate a weekly Snyk report as a GitHub issue. Configure Dependabot for automated minor-version PRs on both npm and pip.                                                                                                               | DO     | P0-T04       | S      |
| P14-T04 | Configure Nginx security headers: Content-Security-Policy (block inline scripts, restrict script sources to CDN), CORS whitelist (Expo app origin + api.lumenly.com only), HSTS with `max-age=31536000; includeSubDomains; preload`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`. Ensure audit log coverage for every write operation across all critical tables. | DO, BE | P0-T02       | M      |
| P14-T05 | Write the security regression test suite: (1) JWT manipulation tests (expired token, `alg: none`, tampered payload); (2) SQL injection payloads on all string input endpoints; (3) GDPR deletion verification (assert all three stores are empty for deleted user); (4) rate-limit enforcement on auth endpoints; (5) OWASP ZAP automated scan against the staging environment. All tests run in the `ci.yml` pipeline on every PR.  | QA, BE | P14-T04      | M      |

---

---

## Phase 15 — Production Deployment

### Phase Summary

**Goal**: Deploy Lumenly to a production-grade cloud environment — containerised API on a managed Kubernetes cluster (or equivalent), MongoDB Atlas with appropriate configuration, managed Redis cluster, Qdrant with replication, CDN for the mobile API, global Nginx/load-balancer configuration, database backup, and a complete runbook for operations, incident response, and rollback.

**Deliverables**:

- Multi-stage production Dockerfiles for `backend/` (uvicorn), `ai/` workers (Celery), and `frontend/` (Expo build)
- Kubernetes Helm charts for `backend` API deployment (HPA configured for 10–100 pods), Celery workers, and Nginx ingress
- MongoDB Atlas cluster with appropriate tier, automated backups, and read replicas for analytics queries
- Managed Redis Cluster (e.g., AWS ElastiCache) with AOF persistence
- Qdrant Cloud or self-hosted with replication factor 2
- CI/CD `cd.yml` pipeline: perform a rolling deployment with zero downtime (no migrations needed for MongoDB)
- Staging environment mirroring production (used for QA, load testing, and canary deployments)
- Operations runbook (`docs/devops_playbook.md`): backup restoration, scaling procedures, incident response, and rollback steps
- Load-test results: Locust simulation of 10,000 concurrent users passing all API endpoints within SLA

**Dependencies**: All prior phases complete and passing in staging

**Estimated Complexity**: Medium-High

**Estimated Duration**: 2 weeks

**Acceptance Criteria**:

- Rolling deployment of a new backend image causes zero downtime (verified by Locust running during deploy)
- `p95` API response time ≤ 200ms for read endpoints and ≤ 2s for coaching WebSocket round-trips under 10,000 concurrent simulated users
- Automated MongoDB Atlas backup completes daily; a restore drill to a point-in-time within the last 24 hours succeeds within 30 minutes
- MongoDB connection pool handles production load with appropriate connection limits and retry logic
- HPA scales the API from 10 to 30 pods within 90 seconds of a load spike pushing CPU above 70%
- All secrets (API keys, JWT private key, database passwords) are stored in AWS Secrets Manager / HashiCorp Vault; no secret appears in any environment variable, Docker layer, or log line

---

### Phase 15 Task Breakdown

| Task ID | Description                                                                                                                                                                                                                                                                                                                                                                                                                                       | Owner      | Dependencies | Effort |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------ | ------ |
| P15-T01 | Write production multi-stage Dockerfiles for (1) the `backend/` FastAPI API (builder stage installs deps; runtime stage runs `uvicorn` as a non-root user), (2) the `ai/` Celery workers (same pattern, worker-specific entrypoints), and (3) the `frontend/` Expo web build. Publish all images to GHCR via the `cd.yml` pipeline on every merge to `main`.                                                                                      | DO         | P0-T04       | M      |
| P15-T02 | Provision managed infrastructure: MongoDB Atlas cluster (appropriate tier for production, automated snapshots, read replicas for analytics queries), AWS ElastiCache Redis Cluster (3 shards × 2 replicas, AOF enabled), and Qdrant Cloud (or self-hosted on EC2 with replication factor 2). Store all connection strings in AWS Secrets Manager. Update `backend/app/core/config.py` to read from Secrets Manager in production.                 | DO         | P15-T01      | L      |
| P15-T03 | Write Helm charts for the `backend` API deployment (resource requests/limits, liveness/readiness probes, HPA targeting 70% CPU), Celery workers (separate chart per worker type), and Nginx ingress (TLS termination, routing rules, rate-limit annotations). Configure staging and production namespaces. Validate HPA scales from 10 to 30 pods within 90 seconds under a CPU spike.                                                            | DO         | P15-T02      | L      |
| P15-T04 | Update the `cd.yml` CI/CD pipeline for zero-downtime production releases: (1) perform a rolling deployment with `maxUnavailable=0`; (2) run smoke tests (health check + one coaching request) against the new pods before marking the release stable; (3) implement a rollback step (previous image tag) triggerable on pipeline failure. MongoDB schema changes are handled via Beanie ODM's automatic collection creation and index management. | DO, BE     | P15-T03      | M      |
| P15-T05 | Run a Locust load test against staging simulating 10,000 concurrent users: key scenarios include login, coaching WebSocket session (1-minute duration), mood check-in, and goal list. Record p50, p95, p99 latencies and error rates. Remediate any endpoint exceeding SLA. Write `docs/devops_playbook.md` covering backup restoration, scaling runbook, incident-response checklist (SEV1–SEV3), on-call rotation, and rollback procedures.     | DO, QA, BE | P15-T04      | L      |

---

---

## Appendix A — Task Count Summary

| Phase                            | Task Count   |
| -------------------------------- | ------------ |
| Phase 0 — Repository Foundation  | 5            |
| Phase 1 — Backend Foundation     | 5            |
| Phase 2 — Authentication & Users | 5            |
| Phase 3 — Conversations          | 5            |
| Phase 4 — Memory Engine          | 6            |
| Phase 5 — Knowledge Brain        | 6            |
| Phase 6 — AI Orchestrator        | 6            |
| Phase 7 — Agent Framework        | 5            |
| Phase 8 — Coaching Engine        | 5            |
| Phase 9 — Wellness Intelligence  | 5            |
| Phase 10 — Voice System          | 5            |
| Phase 11 — Mobile App Foundation | 5            |
| Phase 12 — Subscription System   | 5            |
| Phase 13 — Analytics & Insights  | 5            |
| Phase 14 — Security Hardening    | 5            |
| Phase 15 — Production Deployment | 5            |
| **Total**                        | **83 tasks** |

---

## Appendix B — Dependency Graph (Critical Path)

The critical path to MVP (Q4 2026) runs through:

```
P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7 → P8 → P11 → P12 → P14 → P15
```

Phases that can run in parallel once their prerequisites are met:

- **P9 (Wellness)** can start in parallel with P7/P8 once P3 is complete
- **P10 (Voice)** can start in parallel with P7 once P6 is complete
- **P12 (Subscription)** can start in parallel with P8 once P2 is complete
- **P13 (Analytics)** can start after P8 and P9, in parallel with P14
- **P11 (Mobile)** can begin its scaffold (P11-T01) in parallel with P4 once P2 is done; later tasks depend on backend endpoints being available

---

## Appendix C — Owner Type Legend

| Code | Team                 | Responsible For                                      |
| ---- | -------------------- | ---------------------------------------------------- |
| BE   | Backend Engineering  | FastAPI, PostgreSQL, Redis, Celery, API endpoints    |
| FE   | Frontend Engineering | React Native, Expo, Zustand, UI components           |
| AI   | AI/ML Engineering    | LLM orchestration, agents, memory, embeddings, RAG   |
| DO   | DevOps / Platform    | Docker, Kubernetes, Helm, CI/CD, Nginx, cloud infra  |
| QA   | Quality Assurance    | Test suites, E2E tests, load testing, security scans |

---

## Appendix D — Risk Register

| Risk                                                  | Likelihood | Impact   | Phase(s) Affected | Mitigation                                                                                    |
| ----------------------------------------------------- | ---------- | -------- | ----------------- | --------------------------------------------------------------------------------------------- |
| LLM provider rate limits blocking development         | Medium     | High     | P5–P8             | Use mocked providers in test environments; buy reserved capacity for production               |
| Qdrant scalability under 10M vectors                  | Low        | High     | P4                | Benchmark at 1M vectors during P4; engage Qdrant support if p95 search exceeds 100ms          |
| ElevenLabs API latency variability                    | Medium     | Medium   | P10               | Implement aggressive caching in P10; text-only fallback ensures no user-facing failure        |
| Stripe webhook processing delay causing plan sync lag | Low        | Medium   | P12               | Implement idempotent retry queue; display "pending" plan state in mobile UI                   |
| Security audit discovering architecture-level flaw    | Low        | Critical | P14               | Engage third-party penetration tester before P15; remediation budget reserved                 |
| Mobile app store review delay (Apple / Google)        | Medium     | High     | P11/P15           | Submit for review 4 weeks before launch target; maintain TestFlight/Play Store internal track |

---

_Document prepared by VP of Engineering, Technical Program Manager, and Principal Software Architect._
_Version 1.0 — 2026-06-20 — Approved for immediate engineering execution._
