# Lumenly — The AI Life Operating System

> **One AI that understands your entire life.**
> Lumenly combines long-term memory, personal knowledge (RAG), behavioral analytics, and 8 specialized coaching agents to help people continuously improve every major area of their lives — mental health, productivity, learning, habits, fitness, relationships, career, finances, and life goals — through one unified AI companion.

[![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?logo=githubactions)](./.github) [![Backend](https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi)](./apps/backend) [![Frontend](https://img.shields.io/badge/frontend-React_19-61DAFB?logo=react)](./apps/frontend) [![License](https://img.shields.io/badge/status-private-red)](#)

---

## Table of Contents

1. [What is Lumenly?](#what-is-lumenly)
2. [Key Features](#key-features)
3. [Architecture Overview](#architecture-overview)
4. [Tech Stack](#tech-stack)
5. [Monorepo Structure](#monorepo-structure)
6. [Getting Started](#getting-started)
7. [Environment Variables](#environment-variables)
8. [API Overview](#api-overview)
9. [Testing](#testing)
10. [Observability](#observability)
11. [Security & Privacy](#security--privacy)
12. [Monetization Tiers](#monetization-tiers)
13. [Roadmap](#roadmap)
14. [Documentation](#documentation)
15. [Contributing](#contributing)

---

## What is Lumenly?

Lumenly is **not** a chatbot, a meditation app, or a habit tracker. It is the **AI Operating System for Human Growth**.

Most AI apps answer questions. Lumenly answers:

- *Why are you struggling?*
- *What should you do next?*
- *Which action will create the biggest improvement?*
- *What patterns are holding you back?*

It does this by unifying four capabilities that are normally siloed across 5+ separate apps:

| Capability | What it means for the user |
|---|---|
| **Long-Term Memory** | Lumenly remembers that you study best at night, your motivation drops after poor sleep, and walking improves your mood — across sessions, forever. |
| **Knowledge Brain (RAG)** | Upload your books (Atomic Habits, Deep Work, The Psychology of Money…), and coaching is grounded in *your* content: "Based on Deep Work, your focus sessions should run 8–10 PM — historically this raises your task completion by 31%." |
| **Behavioral Analytics** | Journals, mood check-ins, goals, habits, and (in later phases) wearable data are fused into a 0–100 **Wellness Score** and cross-domain insights. |
| **8 Coaching Agents** | A Life Strategist, Mental Wellness Coach, Habit Coach, Learning Coach, Fitness Coach, Career Coach, Financial Coach, and Relationship Coach, coordinated by a Fusion Engine. |

## Key Features

- **Authentication & RBAC** — JWT (HS256/RS256) with 15-minute access tokens, 7-day rotating refresh tokens, `user`/`admin` roles.
- **Conversational AI Coach** — Text chat over HTTP and structured coaching sessions over **WebSocket** (assessment, nudge, reflection, escalation).
- **Memory Engine** — Short-term conversation memory in Redis, long-term semantic memory in Qdrant with per-user (tenant) isolation, memory ranking, consolidation, and forgetting curves.
- **Knowledge Brain** — PDF/text upload → chunking → embeddings → Qdrant (per-user collections) → RAG retrieval with security validation.
- **Goals, Habits & Journals** — Full domain models with streaks, mood scores (1–10), and semantic search over journal entries.
- **Tool Registry** — Secure, schema-validated tool execution (habit status, goal progress, recent journals) with tenant isolation and security logging.
- **AI Security Layer** — Prompt-injection detection, input sanitization, output filtering, compliance event logging.
- **Rate Limiting** — Redis-based distributed sliding-window limits, per-endpoint limits, WebSocket limits, fail-closed on Redis failure.
- **Predictive Intelligence (roadmap)** — Burnout risk, motivation decline, habit-failure, and goal-abandonment early warnings.
- **Voice Companion “Lumen” (roadmap)** — Groq + ElevenLabs real-time voice coaching with emotional tone detection.

## Architecture Overview

```
┌──────────────────────────┐
│  React 19 + TS + Vite    │  Web app: Login, Chat Workspace, Knowledge Base
└───────────┬──────────────┘
            │ HTTP / WebSocket (JWT)
            ▼
┌───────────────────────────────────────┐
│            FastAPI Backend            │
│  API layer · Auth/RBAC · Middleware   │
│  (rate limiting, metrics, req IDs)    │
├───────────────────────────────────────┤
│  Services (coaching, LLM, vectors)    │
│  AI: RAG · Memory Engine · Agent      │
│  Router · Tool Registry · Security    │
└──┬─────────┬─────────┬─────────┬─────┘
   ▼         ▼         ▼         ▼
PostgreSQL MongoDB   Redis     Qdrant
(users)   (domain   (cache,   (long-term memory,
           models)   rate       knowledge vectors)
           & limits)
        ▲
        └── Groq (primary LLM) · Gemini (fallback) · Embedding providers (OpenAI/Cohere/FastEmbed)
```

**Request flow:** authenticate → rate-limit → retrieve short-term (Redis) + long-term (Qdrant) memory → knowledge retrieval → security validation (prompt-injection, sanitization) → agent routing → LLM generation → output filtering → persist turn → respond.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI (async), Pydantic v2 |
| Auth store | PostgreSQL (async SQLAlchemy 2.0 + Alembic) |
| Domain store | MongoDB Atlas (Motor + Beanie ODM) |
| Cache & limits | Redis (async), sliding-window rate limiting |
| Vector store | Qdrant (per-user collections) |
| LLM providers | Groq — `llama-3.3-70b-versatile` (primary), Gemini — `gemini-2.5-flash` (fallback), Mock (tests) |
| Embeddings | OpenAI `text-embedding-3-small`, Cohere `embed-english-v3.0`, FastEmbed `bge-small-en-v1.5`, Sentence-Transformers `all-MiniLM-L6-v2` |
| Background jobs | Celery + Beat |
| Frontend | React 19, TypeScript, Vite, React Router 7, Axios, Tailwind CSS 4, Lucide icons |
| Monorepo | TurboRepo, npm workspaces |
| Observability | Prometheus (`prometheus-client`), Grafana, structured JSON logging (Loguru) |
| AI voice (planned) | ElevenLabs STT/TTS, Groq inference |

## Monorepo Structure

```
Lumenly/
├── apps/
│   ├── backend/            # FastAPI service
│   │   ├── app/
│   │   │   ├── api/       # endpoints: auth, chat, coaching (WS), documents, journals, memory, vectors, ai, metrics
│   │   │   ├── ai/        # agents, memory, memory_engine, knowledge_brain, rag, llm, embeddings, tools, orchestration, security
│   │   │   ├── core/      # config, security, metrics, logging, celery
│   │   │   ├── db/        # PostgreSQL + MongoDB + Redis + Qdrant clients
│   │   │   ├── models/    # User (PG) + domain models (Mongo/Beanie)
│   │   │   ├── services/  # coaching, llm, vector
│   │   │   └── middleware/# rate limiting (global, per-endpoint), metrics
│   │   ├── alembic/       # SQL migrations
│   │   └── tests/
│   └── frontend/          # React 19 + TS + Vite web app
│       └── src/           # Login, Chat, Knowledge Base pages
├── packages/shared/       # OpenAPI spec, JSON schemas, shared contracts
├── docs/                  # PRD, architecture, requirements, runbooks, decisions (ADRs), project-status
├── infra/                 # Docker Compose, deployment configs
├── monitoring/            # Grafana dashboards, Prometheus config
├── tests/                 # integration, e2e, performance, security suites
├── docker-compose.yml
├── prometheus.yml
├── turbo.json
└── package.json
```

## Getting Started

### Prerequisites

- Node.js ≥ 20, npm ≥ 10
- Python 3.12 (see `apps/backend/.python-version`)
- Docker + Docker Compose
- Running instances of: PostgreSQL, MongoDB, Redis, Qdrant (local Docker Compose or Atlas/managed)

### 1. Clone and install

```bash
git clone https://github.com/MarcelRx/Lumenly.git
cd Lumenly
npm install            # root workspaces
cd apps/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in: database URLs, JWT secrets (32+ chars), Groq/Gemini API keys, Redis, Qdrant
```

See [Environment Variables](#environment-variables). Configuration validation **rejects placeholder secrets in production**.

### 3. Run the infrastructure

```bash
docker compose up -d   # PostgreSQL, MongoDB, Redis, Qdrant
```

### 4. Apply SQL migrations

```bash
cd apps/backend
alembic upgrade head
```

### 5. Start the backend

```bash
uvicorn app.main:app --reload --port 8000
```

Health endpoints: `GET /health/live`, `GET /health/ready`, `GET /health`
Interactive API docs: `http://localhost:8000/docs`

### 6. Start the frontend

```bash
cd apps/frontend
npm run dev            # Vite dev server
```

Or run everything with Turbo:

```bash
npx turbo run dev
```

## Environment Variables

Key variables from `.env.example` (full list in the file):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection (users, auth) |
| `MONGODB_URL` | MongoDB connection (domain collections) |
| `REDIS_URL` | Redis connection (cache, rate limits, short-term memory) |
| `QDRANT_URL` | Qdrant vector DB |
| `JWT_SECRET_KEY` / JWT algorithm & key paths | HS256/RS256 signing |
| `GROQ_API_KEY` | Primary LLM provider |
| `GOOGLE_API_KEY` | Gemini fallback provider |
| `RATE_LIMIT_FAIL_OPEN` | Keep `false` — fail-closed on Redis failure |
| `ENVIRONMENT` | `development` / `staging` / `production` (affects validation strictness) |

## API Overview

Live OpenAPI spec: [`packages/shared/openapi/`](./packages/shared/openapi/). Narrative reference: [`docs/api_contracts.md`](./docs/api_contracts.md).

| Prefix | Description |
|---|---|
| `/api/v1/auth/*` | Register, login, refresh-token rotation |
| `/api/v1/users/*` | User management (RBAC-protected) |
| `/api/v1/documents/*` | Knowledge Brain upload & management |
| `/api/v1/journals/*` | Journal entries with mood scores |
| `/api/v1/memory/*` | Short/long-term memory management |
| `/api/v1/vectors/*` | Vector operations |
| `/v1/ai/*` | AI inference endpoints |
| `/v1/coaching/*` | Coaching sessions — **WebSocket** + HTTP |
| `/v1/metrics` | Prometheus metrics |

## Testing

```bash
# Backend
cd apps/backend
pytest                      # 832+ tests: auth, memory, RAG, rate limiting, tenant isolation, security

# Frontend
cd apps/frontend
npm run build && npm run lint

# Repo-wide test suites
tests/integration  tests/e2e  tests/performance  tests/security  tests/contract
```

Test coverage highlights: multi-worker rate limiting, cross-tenant isolation (memory + vectors + tools), prompt-injection detection, WebSocket limits, memory integration.

## Observability

- **Metrics:** Prometheus scrape config in `prometheus.yml`; `/v1/metrics` endpoint; LLM usage metrics.
- **Dashboards & alerts:** `monitoring/` (Grafana).
- **Logging:** Structured JSON logs with request-ID correlation middleware.
- **Runbooks:** `docs/runbooks/` — backups, service recovery (PG/Mongo/Redis/Qdrant), incident response, LLM provider failure, rollback.

## Security & Privacy

- **Tenant isolation everywhere** — every query, vector search, and tool execution is filtered by `user_id`; cross-tenant attempts are logged as `ComplianceEvent`s.
- **JWT best practice** — short-lived access tokens, rotating refresh tokens, HS256 + RS256 support.
- **AI security** — prompt-injection detection, input sanitization, output filtering (`AISecurityValidator`).
- **Rate limiting** — distributed (Redis), sliding window, per-endpoint and WebSocket limits, fail-closed.
- **Config validation** — rejects placeholder secrets in production; 32+ character secret keys.
- **Planned:** GDPR right-to-be-forgotten endpoint, E2E encryption, on-device inference options, wearable integrations (Apple Health, Google Fit, Oura, Garmin).

## Monetization Tiers

| Tier | Price | Highlights |
|---|---|---|
| Free | $0 | Daily check-ins, mood tracking, basic text coach, 7-day history |
| Plus | $9.99/mo | Unlimited chat, voice coaching, habit tracking, AI journaling, 30-day history |
| Pro | $24.99/mo | Unlimited Knowledge Brain, Learning/Fitness/Career Coaches, advanced insights, 90-day history |
| Elite | $49.99/mo | Multi-agent orchestration, long-term memory, burnout prediction, family accounts |
| Enterprise | Custom | White-label, SSO, admin console, SLA, on-prem options |

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 — Foundation | Repo, CI/CD, API skeleton, Docker | ✅ Done |
| 1 — MVP | Auth, text coach, memory engine, journals/goals/habits, rate limiting, RAG | ✅ Done (832+ tests passing) |
| 2 — V1 | Voice companion, Wellness Score engine, subscriptions, richer web UI | 🚧 In progress |
| 3 — V2 | 8 concrete agents + Fusion Engine, predictive intelligence, wearables | 📋 Planned |
| 4 — Scale | Enterprise, family accounts, i18n, on-prem, advanced analytics | 📋 Planned |

Current gaps tracked in [`docs/architecture/system-architecture.md`](./docs/architecture/system-architecture.md#known-limitations) and [`docs/product/requirements.md`](./docs/product/requirements.md).

## Documentation

| Document | Purpose |
|---|---|
| [`docs/PRD.md`](./docs/PRD.md) | Production PRD — vision, requirements, release criteria |
| [`docs/product/vision.md`](./docs/product/vision.md) · [`requirements.md`](./docs/product/requirements.md) | Product vision & requirement status |
| [`docs/architecture/system-architecture.md`](./docs/architecture/system-architecture.md) | Components, flows, boundaries, limitations |
| [`docs/architecture/ai-architecture.md`](./docs/architecture/ai-architecture.md) | AI stack, providers, RAG, memory |
| [`docs/database_design.md`](./docs/database_design.md) | MongoDB schema & indexing |
| [`docs/api_contracts.md`](./docs/api_contracts.md) | API specification |
| [`docs/Roadmap.md`](./docs/Roadmap.md) | Master development roadmap (phases 0–15) |
| [`docs/project-status/`](./docs/project-status/) | Historical phase reports |
| [`docs/runbooks/`](./docs/runbooks/) | Operational procedures |

## Contributing

1. Branch from `main` using `feature/*`, `fix/*`, or `docs/*`.
2. Read [`docs/README.md`](./docs/README.md) and the relevant architecture docs **before implementing features**.
3. Follow the AI-development workflow ([`docs/ai-development/agent-workflow.md`](./docs/ai-development/agent-workflow.md)) and verification policy for AI-generated code.
4. Add/keep tests green — backend changes require `pytest` passing; frontend requires `tsc -b && vite build` and ESLint.
5. Open a pull request; maintainers review against [`docs/product/requirements.md`](./docs/product/requirements.md).

---

*Lumenly — built as a TurboRepo monorepo; containerized with Docker; monitored with Prometheus + Grafana; deployed via GitHub Actions.*
