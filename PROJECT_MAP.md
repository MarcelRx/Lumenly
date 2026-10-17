# Lumenly — Complete Project Map

> **SUPERSEDED DOCUMENT (retained for historical reference only).**
> This map was authored early in the project and its status claims are outdated. It is preserved because it contains the original product vision, tech-stack rationale, and the authored roadmap snapshot. It is not an authoritative source for current implementation status.
>
> **Authoritative current-state documents:**
> - Current status: docs/project-status/CURRENT_PROJECT_STATUS.md
> - Final executive report: docs/project-status/LUMENLY_COMPLETE_PROJECT_REPORT.md
> - Project structure: docs/project_structure.md
> - Roadmap: docs/Roadmap.md

## Corrections to the historical claims (verified 2026-10-17)

| Historical claim in this file | Verified current reality |
|---|---|
| ai/ modules are empty stubs | AI subsystems are fully implemented under apps/backend/app/ai/ (memory_engine, rag, knowledge_brain, agents, tools, embeddings, llm) with test coverage |
| Tests are empty (tests/ all stubs) | Backend has 51 test files in apps/backend/tests/ (auth, rate limiting, memory, RAG, tenant isolation, metrics, coaching); historical full run: 832 passing / 1 xfailed |
| Backend "14 components done" | Backend substantially complete: auth, users, documents, journals, memory, vectors, AI, coaching WS, metrics, health checks, rate limiting, Celery, monitoring |
| "Phase 1 MVP ~20% complete" | Roadmap Phases 0-2, 4-6, 12.5 complete; Phases 3, 7, 8 partial (framework/scaffolding); 9-11, 13-15 not started |
| Mobile app (React Native/Expo) is a next step | Superseded. Lumenly is a web application only; no mobile code exists or is planned in current specifications |
| apps/backend chat service | Canonical chat path is POST /v1/ai/ask (frontend uses this); chat_router exists but is not registered in main.py |

## What is Lumenly? (original vision - still valid)

**An AI Life Operating System** - a single unified AI companion that helps users improve every major area of their life through long-term memory, personal knowledge integration, behavioral analytics, and 8 specialized coaching agents. Covers: Mental Health, Emotional Intelligence, Productivity, Learning, Habits, Fitness, Relationships, Career, Finances, and Life Goals.

**One-sentence pitch:** "Lumenly is an AI Life Operating System that combines long-term memory, personal knowledge, behavioral analytics, and specialized coaching agents to help people continuously improve every major area of their lives through one unified AI companion."

## Project Structure (as of 2026-10-17)

```
Lumenly/
├── apps/
│   ├── backend/          # FastAPI backend (substantially implemented + tested)
│   │   ├── app/
│   │   │   ├── ai/       # memory_engine, rag, knowledge_brain, agents, tools, embeddings, llm
│   │   │   ├── api/      # endpoints: auth, users, documents, journals, memory, vectors, ai, coaching, metrics
│   │   │   ├── core/     # config, security, metrics, logging, celery
│   │   │   ├── models/   # user (PostgreSQL), domain (MongoDB: goals, habits, journals...)
│   │   │   └── services/ # coaching, llm, vector
│   │   └── tests/        # 51 test files (historical full run: 832 passing)
│   └── frontend/         # React 19 + TypeScript + Vite (Login, Chat, Knowledge Base)
├── packages/shared/       # OpenAPI specs, JSON schemas, contracts
├── docs/                  # Unified documentation (product, architecture, decisions,
│                         #   engineering, security, deployment, ai-development,
│                         #   runbooks, project-status)
├── infra/                 # Docker, Helm, Terraform, Nginx
├── monitoring/            # Prometheus, Grafana, Alertmanager
├── backups/               # Mongo/Postgres backup + restore scripts
├── data/                  # Local Qdrant + Redis data
├── tests/                 # Cross-cutting suite stubs (contract, e2e, integration, perf, security, unit)
└── docker-compose.yml, prometheus.yml, turbo.json
```

## Verified status snapshot (2026-10-17)

- **Backend:** auth (JWT+rotation, RBAC), endpoint-specific Redis rate limiting (fail-closed), memory engine (Redis short-term + Qdrant long-term), RAG orchestrator with AI security, knowledge brain (upload to chunk to embed to search), tool registry (3 tools, tenant isolation), metrics/logging/health checks, cross-tenant authorization - implemented and verified by tests in tree.
- **Frontend:** 3 screens; chat calls POST /v1/ai/ask (code-level verified; live e2e verification open).
- **Not implemented:** concrete specialized agents (framework only), coaching flows (WS scaffolding only), voice, wellness intelligence, personalization, GDPR deletion, goals/habits/journal UIs.
- **Roadmap position:** post-Phase 12.5 (security hardening complete); transition to specialized features. See docs/project-status/CURRENT_PROJECT_STATUS.md.

## Tech Stack (authoritative summary)

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11+), async, Beanie ODM (Motor), SQLAlchemy, Celery |
| Frontend | React 19, TypeScript, Vite 8, React Router DOM 7, Axios, Tailwind CSS 4 |
| Database | PostgreSQL 15 (users, audit), MongoDB 7 (domain models) |
| Vector store | Qdrant (long-term memory + knowledge base) |
| Cache | Redis (short-term memory, rate limiting, caching) |
| AI providers | Groq (primary), Gemini (fallback); embeddings: OpenAI, Cohere, FastEmbed, SentenceTransformers |
| Monorepo | TurboRepo; monitoring: Prometheus, Grafana, Alertmanager |
