---
title: Lumenly – Project Structure
author: Lumenly Engineering Team
date: 2026-06-23
version: 1.1
---

# Lumenly — Project Structure

---

## 1. Monorepo Strategy

- **Single Git repository** containing all code (frontend, backend, AI modules, infra) to keep versioning, CI/CD, and dependency alignment simple.
- **TurboRepo / Nx workspace** provides task orchestration, caching, and incremental builds across languages (TypeScript, Python). Each sub-project lives under its own top-level folder but shares a root `package.json` for tooling versions.
- **Isolation for compliance** – Enterprise-only modules live in `enterprise/` with their own `README` and optional separate CI pipeline.
- **Ownership** – Repo-wide decisions (branching strategy, release cadence) are stewarded by the **Platform Team**; sub-project owners maintain their own folders.

---

## 2. Root Folder Structure

```
Lumenly/                          # Git root
├─ .github/                      # GitHub Actions workflows & reusable actions
├─ .docker/                      # Multi-stage Dockerfiles & compose templates
├─ docs/                         # All documentation (PRD, DB design, architecture)
│   ├─ PRD.md                    # Product Requirements Document
│   ├─ system_architecture.md    # High-level component diagram
│   ├─ database_design.md        # Full DB schema description
│   ├─ ai_system_design.md       # AI/ML architecture blueprint
│   ├─ api_contracts.md          # API specification (OpenAPI-style)
│   ├─ Roadmap.md                # Master development roadmap
│   └─ project_structure.md      # <-- you are reading this file
├─ infra/                        # IaC (Docker Compose, Helm, Terraform stubs)
├─ apps/
│   ├─ frontend/                 # React 19 + TypeScript + Vite web application
│   └─ backend/                  # FastAPI service with AI components
├─ tests/                        # Integration & end-to-end test suites
├─ scripts/                      # Helper scripts (data seeding, MongoDB initialization)
├─ shared/                       # Language-agnostic contracts (OpenAPI spec, JSON schemas)
├─ .env.example                  # Template for environment variables
├─ docker-compose.yml            # Local dev stack (MongoDB, Redis, Qdrant, API, UI)
└─ README.md
```

Each top-level folder has a **Purpose**, **Responsibilities**, and **Ownership** section described below.

---

## 3. Frontend Structure (`apps/frontend/`)

**Purpose** – Deliver the web application interface via React 19 + TypeScript + Vite.

**Current Implementation Status:** Minimal implementation with 3 screens only.

```
apps/frontend/
├─ src/
│   ├─ App.tsx                   # Main application with routing
│   ├─ main.tsx                  # Application entry point
│   ├─ Login.tsx                 # Login screen (email/password authentication)
│   ├─ Chat.tsx                  # AI coaching chat interface
│   ├─ pages/
│   │   └─ KnowledgeBase.tsx      # Knowledge Base dashboard
│   ├─ assets/                   # Static assets
│   ├─ index.css                 # Global styles
│   └─ App.css                   # App component styles
├─ public/                       # Public assets
├─ dist/                         # Build output
├─ index.html                    # HTML entry point
├─ package.json                  # Dependencies and scripts
├─ vite.config.ts                # Vite configuration
├─ tsconfig.json                 # TypeScript configuration
└─ eslint.config.js              # ESLint configuration
```

**Technology Stack:**

- React 19
- TypeScript
- Vite (build tool)
- React Router DOM (client-side routing)
- Axios (HTTP client)
- Tailwind CSS (styling)
- Lucide React (icons)

**Implemented Screens:**

- Login (`/login`) - Email/password authentication with JWT token storage
- Chat Workspace (`/`) - HTTP-based AI coaching interface
- Knowledge Base (`/kb`) - Document management dashboard

**Not Yet Implemented:**

- Goal tracking UI
- Habit tracking UI
- Journal entry UI
- Wellness dashboard
- Profile/settings
- Registration screen
- WebSocket-based real-time chat
- Mobile-responsive design optimizations

**Responsibilities** – UI rendering, client-side validation, HTTP API communication, authentication state management.
**Ownership** – **Frontend Squad** (React engineers, UX designers).

---

## 4. Backend Structure (`apps/backend/`)

**Purpose** – Core API, business logic, authentication, and orchestration of AI services.

```
apps/backend/
├─ app/
│   ├─ api/                      # FastAPI routers (v1) grouped by domain
│   │   ├─ auth.py               # /v1/auth/* — register, login, logout, refresh
│   │   ├─ users.py              # /v1/users/* — user CRUD, profile
│   │   ├─ coaching.py           # /v1/coaching/* — sessions, WebSocket
│   │   ├─ goals.py              # /v1/goals/* — CRUD + progress
│   │   ├─ habits.py             # /v1/habits/* — CRUD + check-in
│   │   ├─ journal.py            # /v1/journal/* — entries
│   │   ├─ moods.py              # /v1/moods/* — mood tracking & trends
│   │   ├─ memory.py             # /v1/memory/* — semantic memory
│   │   ├─ knowledge.py          # /v1/knowledge/* — document upload
│   │   ├─ rag.py                # /v1/rag/* — RAG query, reindex
│   │   ├─ wellness.py           # /v1/wellness/* — dashboard, score, trends
│   │   ├─ voice.py              # /v1/voice/* — transcribe, synthesize, chat
│   │   ├─ insights.py           # /v1/insights/* — daily/weekly/monthly
│   │   ├─ subscription.py       # /v1/subscription/* — plans, upgrade, cancel
│   │   └─ admin.py              # /v1/admin/* — analytics console (admin only)
│   ├─ core/                     # Core utilities
│   │   ├─ config.py             # Pydantic BaseSettings (all env vars)
│   │   ├─ mongodb.py            # MongoDB connection pool & Beanie ODM initialization
│   │   ├─ redis.py              # Async Redis client wrapper
│   │   ├─ qdrant.py             # Qdrant client wrapper
│   │   └─ logging.py            # Structured JSON logging (structlog)
│   ├─ db/                       # Beanie ODM document models (Pydantic-based)
│   │   ├─ user.py               # User document model
│   │   ├─ profile.py            # Profile document model
│   │   ├─ conversation.py       # Conversation document model
│   │   ├─ journal.py            # JournalEntry document model
│   │   ├─ goal.py               # Goal document model
│   │   ├─ habit.py              # Habit document model
│   │   ├─ mood.py               # MoodEntry document model
│   │   ├─ insight.py            # AiInsight document model
│   │   ├─ document.py           # KnowledgeDocument model
│   │   ├─ memory_link.py        # MemoryLink document model
│   │   └─ challenge.py          # WellnessChallenge document model
│   ├─ services/                 # Service layer (subscription, billing, webhooks)
│   ├─ ai/                       # Thin adapters that call the `ai/` package
│   │   ├─ llm_router.py         # LLM provider routing (Groq / Gemini)
│   │   ├─ context_builder.py    # Context assembly for LLM prompts
│   │   └─ personalization.py    # User Blueprint computation
│   └─ middleware/               # Auth, rate-limit, request-ID middleware
├─ tests/                        # Pytest unit & integration tests
├─ scripts/                      # Data seed scripts, MongoDB initialization utilities
├─ Dockerfile                    # Multi-stage: builder + runtime (uvicorn)
├─ pyproject.toml
└─ requirements.txt
```

**Responsibilities** – REST/WebSocket API, data validation, transaction management, security, queuing background jobs.
**Ownership** – **Backend Team** (FastAPI engineers, data engineers).

### MongoDB & Beanie ODM Setup

- **Beanie ODM** is used as the MongoDB object-document mapper, built on top of Pydantic for type safety and validation.
- All document models inherit from `beanie.Document` and define fields as Pydantic models.
- MongoDB connection is established via `motor` (async MongoDB driver) with connection pooling.
- Indexes are defined on document models using Beanie's index decorators.
- Document relationships use MongoDB's document reference pattern or embedded documents as appropriate.
- Transactions are supported via MongoDB sessions for multi-document operations.

---

## 5. AI Modules Structure (`ai/`)

### 5.1 Knowledge Brain (`ai/knowledge_brain/`)

- **Purpose** – Central LLM orchestration (Groq, Gemini) for all prompt engineering and RAG operations.
- **Responsibilities** – Prompt templating, model selection, retry & timeout handling, streaming responses, document ingestion.
- **Ownership** – **AI Core Team** (LLM specialists).

### 5.2 Memory Engine (`ai/memory_engine/`)

- **Purpose** – Manage semantic memory lifecycle, interact with Qdrant, handle vector upserts & retrieval.
- **Responsibilities** – Chunking, embedding generation (via Groq/Gemini), metadata enrichment, TTL enforcement.
- **Ownership** – **AI Core Team**.

### 5.3 Agent System (`ai/agent_system/`)

- **Purpose** – Run multi-agent orchestrations (workflow, parallel execution) for complex tasks.
- **Responsibilities** – Agent definition registry, context propagation, result aggregation, fault isolation, safety layer.
- **8 Domain Agents**: Life Strategist, Mental Wellness Coach, Habit Coach, Learning Coach, Fitness Coach, Career Coach, Financial Coach, Relationship Coach.
- **Ownership** – **AI Core Team**.

### 5.4 Voice (`ai/voice/`)

- **Purpose** – Text-to-speech via ElevenLabs and speech-to-text transcription.
- **Responsibilities** – Audio generation, audio caching in Redis, streaming to mobile client.
- **Ownership** – **AI Core Team** (speech engineers).

---

## 6. Memory Engine Structure — Detailed View

```
ai/memory_engine/
├─ __init__.py
├─ chunker.py                    # Text chunking strategies (sliding window, semantic)
├─ embedder.py                   # Wrapper for Groq / Gemini embeddings (batched)
├─ qdrant_client.py              # Connection pool & CRUD helpers
├─ schemas.py                    # Pydantic models for vector metadata
├─ retention.py                  # Periodic cleanup per DB retention policy
└─ utils.py                      # Helper functions (hashing, batching)
```

**Ownership** – **AI Core Team**.

---

## 7. Knowledge Brain Structure — Detailed View

```
ai/knowledge_brain/
├─ __init__.py
├─ provider/
│   ├─ groq.py                   # Groq API client (chat/completions + embeddings)
│   └─ gemini.py                 # Google Gemini client
├─ prompt_templates/             # Jinja-style prompt files per domain
│   ├─ mental_health.j2
│   ├─ productivity.j2
│   ├─ learning.j2
│   ├─ fitness.j2
│   ├─ career.j2
│   ├─ finance.j2
│   └─ relationships.j2
├─ response_parser.py            # Structured output extraction & JSON validation
├─ rate_limiter.py               # Per-model token budgeting
└─ cache.py                      # In-memory LRU cache for repeated prompts
```

**Ownership** – **AI Core Team**.

---

## 8. Agent System Structure — Detailed View

```
ai/agent_system/
├─ __init__.py
├─ orchestrator.py               # Entry point for all AI workflow execution
├─ agent_registry.py             # Catalog of available agents & their JSON-Schema contracts
├─ executor.py                   # Runs agents concurrently (asyncio.gather) or sequentially
├─ fusion.py                     # Fusion Engine: merges multi-agent responses
├─ safety.py                     # Safety Layer (injection detection, toxicity, crisis escalation)
├─ agents/                       # One module per domain agent
│   ├─ life_strategist.py
│   ├─ mental_wellness.py
│   ├─ habit_coach.py
│   ├─ learning_coach.py
│   ├─ fitness_coach.py
│   ├─ career_coach.py
│   ├─ financial_coach.py
│   └─ relationship_coach.py
├─ schemas/                      # JSON-Schema definitions for StructuredOutput
├─ logger.py                     # Structured logging for auditability
└─ hooks/                        # Extensibility points (pre-run safety scan, post-run toxicity filter)
```

**Ownership** – **AI Core Team**.

---

## 9. API Structure (within `backend/app/api/`)

- **auth/** – JWT issuance, refresh flow, password reset.
- **users/** – Profile CRUD, privacy settings, GDPR data export.
- **coaching/** – WebSocket coaching sessions, session history, AI insights.
- **goals/** – CRUD + progress recording, milestone tracking.
- **habits/** – Habit loop management, streaks, daily check-ins.
- **journal/** – Journal entries with mood tagging.
- **moods/** – Mood snapshots and trend aggregation.
- **memory/** – Vector upsert/search endpoints (semantic recall).
- **knowledge/** – Document upload (Knowledge Brain).
- **rag/** – RAG query endpoint, admin re-index.
- **wellness/** – Composite dashboard, wellness score, trends, recommendations.
- **voice/** – Speech-to-text, text-to-speech, voice chat WebSocket.
- **insights/** – Daily, weekly, monthly AI insight endpoints.
- **subscription/** – Plan management, Stripe integration.
- **admin/** – Enterprise admin console (feature flags, tenant management, analytics).

Each router is versioned (`/api/v1/...`) and documented via OpenAPI which lives under `shared/openapi.yaml`.
**Ownership** – Backend Team, with AI Team reviewing the AI-related routes.

---

## 10. Infrastructure Structure (`infra/`)

```
infra/
├─ docker-compose.yml            # Local dev stack (MongoDB, Redis, Qdrant, API, UI)
├─ nginx/
│   ├─ Dockerfile                # Nginx with TLS termination & reverse-proxy config
│   └─ conf.d/
│       └─ lumenly.conf          # Route /api to FastAPI, / to Expo web fallback
├─ helm/                         # Helm charts for K8s deployments
│   ├─ api/
│   │   └─ Chart.yaml
│   └─ workers/
│       └─ Chart.yaml
├─ terraform/                    # Cloud infra (VPC, Atlas, ElastiCache, Qdrant)
│   └─ main.tf
└─ scripts/
    └─ deploy.sh                 # CI-CD entry point for Docker Hub / GHCR
```

**Purpose** – Provide reproducible environments for dev, CI, and production.
**Ownership** – **Platform Ops Team**.

---

## 11. Testing Structure (`tests/` & `frontend/__tests__`)

- **unit/** – FastAPI unit tests (pytest), React Native unit tests (Jest).
- **integration/** – End-to-end API tests using HTTPX + Docker Compose.
- **e2e/** – Detox/Playwright mobile flows exercising the full stack.
- **contract/** – OpenAPI schema validation against actual responses.
- **performance/** – Load testing scripts (Locust for API, Artillery for WebSocket).
- **security/** – OWASP ZAP scans, JWT manipulation tests, SQL injection payloads.

**Ownership** – QA Engineering team, with test-ownership tags in each folder.

---

## 12. CI/CD Structure (`.github/`)

```
.github/
├─ workflows/
│   ├─ ci.yml                    # Lint, unit tests, integration, security scan on PRs
│   ├─ cd.yml                    # Publish Docker images, deploy to staging on merge to main
│   └─ release.yml               # Tag-based semantic version release, changelog generation
├─ actions/
│   ├─ setup-python.yml          # Reusable action for Python env
│   └─ setup-node.yml            # Reusable action for Node.js env
└─ dependabot.yml                # Auto-updates for npm & pip deps
```

- **ci.yml** runs on every push/PR: lint (ESLint, Ruff), test matrix (frontend, backend, AI modules), security scan (Snyk, bandit).
- **cd.yml** builds multi-arch Docker images, pushes to GHCR, and spins up a staging environment behind Nginx.
- **release.yml** tags a new version, generates a `CHANGELOG.md`, and notifies Slack.

**Ownership** – Platform Team (DevOps) in partnership with product owners.

---

## 13. Documentation Structure (`docs/`)

| File                              | Description                                           |
| --------------------------------- | ----------------------------------------------------- |
| `PRD.md`                          | Approved Product Requirements Document                |
| `system_architecture.md`          | High-level component diagram & architecture decisions |
| `database_design.md`              | Full MongoDB schema & indexing strategy               |
| `ai_system_design.md`             | AI/ML architecture blueprint                          |
| `api_contracts.md`                | OpenAPI-style API specification                       |
| `Roadmap.md`                      | Master development roadmap (phases 0–15)              |
| `project_structure.md`            | This file                                             |
| `deployment_guide.md` _(planned)_ | How to spin up local dev, staging, production         |
| `devops_playbook.md` _(planned)_  | Runbooks for backups, scaling, incident response      |
| `contributing.md` _(planned)_     | Code style, PR process, branching model               |

**Ownership** – Documentation is a shared responsibility; a dedicated **Docs Owner** ensures consistency.

---

_Prepared by the Lumenly Engineering Team — 2026-06-23._
