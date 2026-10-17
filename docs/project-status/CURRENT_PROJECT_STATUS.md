# Lumenly — Current Project Status

**Authoritative current-state document. Last audited: 2026-10-17 against `main` @ `7a3dab8`.**
**Status labels:** Implemented and verified · Implemented, verification incomplete · Partially implemented · Framework/scaffolding only · Planned · Blocked · Unverified · Superseded

---

## 1. Original project vision (evidence-based)

Lumenly is intended to be an **AI-native life operating system**: a web application that delivers personalized wellness coaching through specialized AI agents across life domains (mental health, habits, fitness, career, finance, relationships, learning, life strategy), combining long-term memory, personal knowledge retrieval (RAG), secure tool execution, and proactive coaching flows.

- Evidence: `docs/project_idea.text`, `docs/PRD.md`, `docs/Roadmap.md`, `docs/product/vision.md`, `PROJECT_MAP.md` (historical).
- **Confirmed:** Lumenly is a **web application** (React 19 + TypeScript + Vite frontend, FastAPI backend). No React Native / Expo code exists in the repository. Mobile mentions remaining in `docs/Roadmap.md` (Phase 10/11/15) are **legacy text from the original authored roadmap**, superseded by the web-application decision — see `docs/architecture/system-architecture.md` (React Native claim fixed during documentation unification).

## 2. Confirmed product requirements

Authoritative requirements live in `docs/product/requirements.md` (current) and `docs/PRD.md` (authored). Core confirmed requirements:

1. Authentication with JWT access/refresh tokens and RBAC
2. Multi-agent AI coaching with agent routing (8 agent types)
3. Memory: short-term (Redis) and long-term (Qdrant) with tenant isolation
4. Knowledge brain: document upload, chunking, embedding, semantic search
5. Tool registry with authorization, validation, tenant isolation
6. Coaching flows: assessment, nudge, reflection, escalation (WebSocket)
7. Rate limiting and security hardening (Phase 12.5)
8. Observability: metrics, logging, health checks

## 3. What has been implemented (verified by code + tests in tree)

| Subsystem | Status | Evidence |
|---|---|---|
| FastAPI app with routers, middleware, error handlers | Implemented and verified | `apps/backend/app/main.py`, `test_main.py` |
| Authentication (register/login/refresh/rotation, JWT HS256/RS256) | Implemented and verified | `app/api/endpoints/auth.py`, `test_auth.py` (25 KB) |
| Rate limiting (Redis, endpoint-specific, fail-closed, multi-worker) | Implemented and verified | `test_rate_limiting.py` + 5 more rate-limit test files |
| Memory engine (short-term Redis, long-term Qdrant, manager, consolidation) | Implemented and verified | `app/ai/memory_engine/`, 5 memory test files |
| RAG orchestrator with AI security (injection detection, sanitization, output filtering) | Implemented and verified | `app/ai/rag/`, `app/ai/security.py`, `test_rag_orchestrator.py` |
| Knowledge brain (upload, chunking, embeddings, Qdrant, semantic search) | Implemented and verified | `app/ai/knowledge_brain/`, `test_documents.py`, `test_vectors.py` |
| Tool registry (3 tools, authorization, tenant isolation) | Implemented and verified | `app/ai/tools/`, `test_tool_registry_security.py`, `test_tool_security_tenant_isolation.py` |
| LLM providers (Groq, Gemini, mock factory) | Implemented and verified | `app/ai/llm/`, `test_ai_llm_interface.py` |
| Embedding providers (OpenAI, Cohere, FastEmbed, SentenceTransformers) | Implemented and verified | `app/ai/embeddings/`, `test_embedding_providers.py` |
| Metrics/logging/health checks (Prometheus, liveness/readiness) | Implemented and verified | `app/core/metrics.py`, `monitoring/`, 6 metrics test files |
| Multi-database architecture (PostgreSQL, MongoDB/Beanie, Redis, Qdrant) | Implemented and verified | `docs/decisions/ADR-0001`, `test_database.py`, `test_infrastructure.py` |
| Cross-tenant authorization & isolation | Implemented and verified | `test_cross_tenant_authorization.py` (26 KB) |
| Frontend Login / Chat / Knowledge Base screens | Implemented, verification incomplete | `apps/frontend/src/` (3 screens) |
| Chat integration (frontend → `POST /v1/ai/ask`) | Implemented, verification incomplete (code-level verified; e2e not run) | `Chat.tsx` calls `/v1/ai/ask` with `{ query }`, reads `{ answer, retrieval_stats }` — matches `app/api/endpoints/ai.py` |

## 4. What is implemented but not adequately tested / verified

- **Frontend build & lint**: last verified during Phase H (build + lint passed); no frontend unit tests exist. No end-to-end chat run recorded against a live backend.
- **Production deployment**: Docker/Helm/Terraform/CI exist but were never exercised in production (unverified).
- **TLS / load behavior at scale**: configuration-dependent, unverified.

## 5. Partially implemented (framework / scaffolding only)

- **Agent system**: `BaseAgent`, keyword-based `AgentRouter`, `AgentType` enum (8 types) exist — **no concrete agent implementations**.
- **Coaching engine**: WebSocket endpoint + session types exist — assessment/nudge/reflection/escalation flows not implemented (`coaching.py` is 30 KB of scaffolding + 5 coaching test files cover architecture/security, not full flows).
- **Conversations**: models/endpoints exist; full conversation flows incomplete.
- **Chat router**: `app/api/endpoints/chat.py` exists but is **not registered in `main.py`** (dead route; `/v1/ai/ask` is the canonical chat path).

## 6. Not implemented

- Concrete specialized agents (Fitness Coach, Habit Coach, etc.) and agent fusion engine
- Voice pipeline (ElevenLabs) — Phase 10 (not started)
- Wellness intelligence engine — Phase 9 (not started)
- Personalization engine (user blueprint)
- GDPR data deletion (right-to-be-forgotten)
- Frontend screens: goals, habits, journal, wellness dashboard, profile/settings, registration
- WebSocket real-time chat; circuit breakers; session invalidation; SIEM integration

## 7. Blocked items and why

- **End-to-end chat verification** — blocked by unavailable Docker infrastructure (PostgreSQL, MongoDB, Redis, Qdrant) and LLM provider keys in the audit environment. Code-level fix is committed; live verification remains open.
- **Fresh full backend test run** — same infrastructure blocker. Last full recorded run: 832 passing / 1 xfailed / 0 failures (Phase 12.5, commit `4a93c03`), executed with Docker services running. This is a **historical result**, not a fresh one.

## 8. Previous development phases

| Phase | Scope | Status | Evidence / confidence |
|---|---|---|---|
| 0 — Repository foundation | Monorepo, CI, docs | Complete | Repo structure, `.github/workflows/ci.yml` — high |
| 1 — Backend foundation | FastAPI skeleton, 4-database architecture | Complete | `app/main.py`, ADR-0001 — high |
| 2 — Authentication & users | JWT, RBAC, CRUD | Complete | `auth.py`, `test_auth.py` — high |
| 3 — Conversations | Models, endpoints, WS scaffolding | Partially complete | `chat.py` (unregistered router) — high |
| 4 — Memory engine | Redis + Qdrant memory | Complete | `app/ai/memory_engine/` + tests — high |
| 5 — Knowledge brain | Upload → chunk → embed → search | Complete | `app/ai/knowledge_brain/` + tests — high |
| 6 — AI orchestrator | RAG pipeline | Complete | `app/ai/rag/` + tests — high |
| 7 — Agent framework | BaseAgent + router | Framework only | `app/ai/agents/` — high |
| 8 — Coaching engine | WS endpoint + session types | Scaffolding only | `coaching.py` — high |
| 9–11 — Wellness / voice / mobile | — | Not started | Roadmap only — high (mobile superseded by web decision) |
| 12 (+12.5) — Security hardening | Rate limiting, tenant isolation | Complete | Phase 12.5 reports (in Git history), 31 rate-limit tests — high |
| 13–15 — Analytics / subscriptions / production deploy | — | Not started / unverified | Roadmap only — high |
| Docs consolidation + accuracy audit + Phases A–H mission | Documentation unification, chat repair | Complete | `docs/project-status/` reports — high |

Historical note: root-level Phase 12.5 reports were deleted from the working tree during the documentation reorganization and are preserved **in Git history** (recoverable, e.g. `git show 887b52a:PHASE_12_5_FINAL_REPORT.md`). Their findings were migrated into the Phase E-F-G report and this status document.

## 9. Current engineering focus

Transition from foundation to specialized features: the functioning core (auth → memory/RAG → chat) is in place; the next value and risk-reduction lies in (1) live end-to-end verification of the repaired chat path, then (2) concrete agent implementations.

## 10. What should happen next (ordered)

1. **Verify chat integration end-to-end** — start Docker stack, backend, configure LLM keys, log in, send a real query through the UI. Acceptance: real response rendered, memory badge populated. Effort: ~0.5–1 day. Confidence: high (code contract verified).
2. **Implement 2–3 concrete agents** (e.g. Life Strategist, Habit Coach, Fitness Coach) with prompts, tool registration, routing tests. Acceptance: routed correctly by keyword router, agent-specific tests pass. Effort: 2–3 weeks.
3. **Implement coaching flows** (assessment, nudge, reflection, escalation) over the existing WebSocket scaffolding. Acceptance: flow-level tests pass; crisis-escalation guardrails verified.
4. **Frontend screen expansion** (goals, habits, journal, wellness dashboard). Acceptance: screens call existing verified backend endpoints; build + lint pass.
5. **GDPR data deletion** (right-to-be-forgotten across all four stores). Acceptance: deletion test suite passes.
6. Register-or-remove the dead `chat_router` in `main.py` (small cleanup, decision needed).

## 11. Evidence that the next milestone is complete

- Milestone 1: recorded end-to-end transcript/screenshots + a passing smoke test script (`scripts/`) against a running stack; frontend build/lint green.
- Milestone 2: agent routing tests + concrete agent unit tests in `apps/backend/tests/`, all passing on Docker stack.

---

**Unresolved questions:** (a) should `/v1/chat/ask` router be registered or removed? (b) will agent routing stay keyword-based or migrate to LLM-based (ADR-0003 records the accepted decision and its planned migration)? (c) legal review of GDPR deletion scope (requires qualified review — not determined here).

**See also:** [LUMENLY_COMPLETE_PROJECT_REPORT.md](./LUMENLY_COMPLETE_PROJECT_REPORT.md) · [README.md](./README.md) · [PHASE_H_VALIDATION_REPORT.md](./PHASE_H_VALIDATION_REPORT.md)
