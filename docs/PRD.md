---
title: Lumenly – Product Requirements Document (PRD)
author: Lumenly Product & Architecture Team
date: 2026-10-17
version: 2.0
status: PRODUCTION
supersedes: PRD v1.1 (2026-06-23)
audience: Engineering, Product, Security, Operations
---

# Lumenly — Production PRD

## 1. Executive Summary

Lumenly is an **AI-native Life Operating System**: a single, conversational AI companion that consolidates ten personal-development domains — mental health, emotional intelligence, productivity, learning, habit formation, physical fitness, relationships, career growth, financial discipline, and life-goal management — into one product.

Unlike the 5+ fragmented apps users juggle today, Lumenly unifies **long-term memory**, **personal knowledge (RAG)**, **behavioral analytics**, and **multi-agent AI coaching**, so guidance is persistent, personal, and grounded in each user's own data.

This PRD defines the **final production product** to be delivered and maintained on `main`. It supersedes v1.1 and is aligned with the implemented architecture (verified against the codebase: FastAPI backend, React 19 web app, PostgreSQL + MongoDB + Redis + Qdrant, Groq/Gemini LLM routing, 832+ passing tests).

> **One-sentence pitch:** *Lumenly is an AI Life Operating System that combines long-term memory, personal knowledge, behavioral analytics, and specialized coaching agents to help people continuously improve every major area of their lives through one unified AI companion.*

---

## 2. Vision & Mission

- **Vision:** Become the single AI companion that *knows* a user's entire life story and continuously guides them toward their highest-potential self.
- **Mission:** Build a unified, privacy-first AI platform that **learns**, **remembers**, and **guides** users toward their optimal selves through personalized, cross-domain insights and actionable coaching.

**Positioning:** Lumenly is **not** a chatbot, meditation app, or habit tracker. It is the *AI Operating System for Human Growth*. It answers: *Why are you struggling? What should you do next? What action creates the biggest improvement? What patterns are holding you back?*

---

## 3. Market Opportunity

| Segment | TAM (2025) | SAM (2026) | SOM (3-yr) |
|---|---|---|---|
| Self-Improvement & Wellness Apps | $180 B | $45 B | $540 M |
| Productivity & Task-Management | $60 B | $12 B | $144 M |
| Digital Coaching & Therapy | $30 B | $6 B | $72 M |
| **Combined addressable market** | **$270 B** | **$63 B** | **$756 M** |

~30% of users in these segments report willingness to pay $10–25/month for an integrated, AI-driven experience that eliminates app fragmentation.

---

## 4. User Personas

| Persona | Age | Occupation | Core pain points | Desired outcomes |
|---|---|---|---|---|
| Growth-Focused Professional | 28–38 | Software Engineer, PM | Multiple apps, no reflection time | Unified daily check-in, data-driven habit loops |
| Wellness-First Urbanite | 30–45 | Marketing, Consulting | Inconsistent fitness & mental-health tracking | Holistic Wellness Score, guided routines |
| Aspiring Entrepreneur | 25–35 | Founder, Side-Hustler | Overwhelmed by goal frameworks | AI-crafted roadmap, milestone tracking |
| Life-Transition Seeker | 40–55 | Mid-career professional | Lack of purpose after major life change | Structured reflection, career-pivot planning |
| Financially-Savvy Saver | 30–50 | Analyst, Freelancer | Scattered budgeting tools | Integrated discipline, goal-linked saving |

---

## 5. Core Problems (Jobs to Be Done)

1. **Fragmentation** — 5+ separate apps → data silos, low adherence.
2. **Context-switch overhead** — reduces focus and intervention impact.
3. **Generic advice** — one-size-fits-all recommendations ignore personal context.
4. **Memory decay** — insights from previous sessions are lost; no persistent cross-domain memory.
5. **Motivation fatigue** — sparse, isolated nudges lose effectiveness.
6. **Privacy concerns** — centralized personal data requires clear, verifiable controls.

---

## 6. Product Architecture Layers

| Layer | Components | Production status |
|---|---|---|
| **L1 — User Data Layer** | Journals, mood check-ins, goals, habits, tasks; document uploads; wearable integrations (future) | ✅ Manual inputs + uploads live; wearables future |
| **L2 — Memory System** | Short-term (Redis), long-term semantic memory (Qdrant), ranking, consolidation, forgetting curves | ✅ Implemented & tested |
| **L3 — Knowledge Brain** | Upload → chunk → embed → Qdrant (per-user) → RAG retrieval with tenant isolation | ✅ Implemented & tested |
| **L4 — Life Intelligence Engine** | Wellness Score (0–100), predictive alerts, 8-agent orchestration, Fusion Engine | 🚧 Score/agents/predictive in progress |

---

## 7. Functional Requirements

### 7.1 Authentication & Authorization
- Email/password registration and login (bcrypt) — **done**
- JWT: 15-min access tokens, 7-day rotating refresh tokens, HS256 + RS256 — **done**
- RBAC (`user`, `admin`), `require_role` dependency — **done**

### 7.2 AI Coaching
- Text chat via HTTP (frontend) and structured coaching sessions via **WebSocket** — **done**
- Four session types: assessment, nudge, reflection, escalation — **done**
- Structured 30-minute assessment flow — **partial, complete in R1**
- WebSocket rate limiting (connection/message/tool-call) and message-size validation — **done**

### 7.3 Memory
- Short-term conversation history in Redis — **done**
- Long-term memories as vectors in Qdrant with semantic retrieval — **done**
- Tenant isolation in all retrieval paths — **done & cross-tenant tested**

### 7.4 Knowledge Brain (RAG)
- PDF/text upload, chunking, embeddings (OpenAI/Cohere/FastEmbed/ST), per-user Qdrant storage — **done**
- Grounded responses citing user content — **done**

### 7.5 Goals, Habits, Journals
- CRUD goals with completion tracking; habits with frequency + streak counts; journals with 1–10 mood scores and semantic search — **done (backend); web UI for goals/habits/journals ships in R1**

### 7.6 Agent System
- `BaseAgent` framework, keyword-based `AgentRouter`, tool registry — **done**
- **8 concrete agents** (Life Strategist, Mental Wellness, Habit, Learning, Fitness, Career, Financial, Relationship) — **ship in R2** (currently framework-only)
- Fusion Engine multi-agent orchestration — **ship in R3**

### 7.7 Tool Execution
- `ToolRegistry` with schema validation, tenant isolation, security logging; default tools: `check_habit_status`, `get_goal_progress`, `get_recent_journals` — **done**

### 7.8 Wellness & Predictive Intelligence
- Wellness Score (0–100): Sleep 20%, Mood 20%, Productivity 15%, Habits 15%, Fitness 10%, Learning 10%, Relationships 10% — **ship in R2**
- Predictive alerts: burnout, motivation decline, habit failure, stress escalation, goal abandonment — **ship in R3**

### 7.9 Voice Companion ("Lumen")
- Groq inference + ElevenLabs STT/TTS, real-time coaching, voice journaling, emotional tone detection — **ship in R3**

### 7.10 Challenges System
- AI-generated 7-day / 30-day / custom sprints bundling goals, habits, tasks — **ship in R3**

---

## 8. Non-Functional Requirements

| Category | Requirement | Status |
|---|---|---|
| Performance | API < 500 ms (non-AI); AI coaching < 5 s | Non-AI verified; AI target pending load tests |
| Reliability | 99.9% uptime; graceful DB failure; LLM fallback chain | LLM fallback + circuit breakers required for R2 |
| Security | Tenant isolation at all layers; prompt-injection detection; input sanitization; output filtering; rate limiting (Redis sliding window, per-endpoint, fail-closed) | ✅ Implemented & tested |
| Privacy | GDPR/CCPA; right-to-be-forgotten endpoint | Deletion API required before public launch (R1 blocker) |
| Observability | Prometheus metrics, structured JSON logs, request-ID correlation, health endpoints (`/health/live`, `/health/ready`), Grafana dashboards, runbooks | ✅ Implemented |
| Scalability | Stateless API workers, distributed rate limiting, Mongo Atlas sharding, Qdrant sharding | Designed; K8s deployment in R2 |
| Compliance | `ComplianceEvent` audit logging, severity levels | ✅ Implemented |

---

## 9. Release Plan (Definition of "Final Production")

| Release | Scope | Exit criteria |
|---|---|---|
| **R1 — Production MVP** (target: merge to `main`) | Auth ✅, chat ✅, coaching WS ✅, memory ✅, RAG ✅, journals/goals/habits ✅, rate limiting ✅, security ✅, web UI for goals/habits/journals, GDPR deletion endpoint, LLM fallback chain, prod deployment config | All tests green; zero known cross-tenant isolation defects; deployment verified in staging; secrets validated in prod mode |
| **R2 — V1** | 8 concrete agents, Wellness Score engine, subscriptions/billing (Free/Plus/Pro/Elite), richer dashboard, Kubernetes deployment, LLM provider fallback + circuit breakers | Paid tiers live; Wellness Score in dashboard; 99.9% uptime measured |
| **R3 — V2** | Fusion Engine orchestration, predictive intelligence, voice companion, challenges, wearable integrations (Apple Health, Google Fit, Oura, Garmin) | Voice coaching GA; ≥3 predictive alert types in production |
| **R4 — Scale** | Enterprise (SSO, white-label, admin console, SLA, on-prem), family accounts, i18n, advanced analytics | Enterprise pilot signed |

---

## 10. Monetization

| Tier | Price | Features |
|---|---|---|
| Free | $0 | Daily check-ins, mood tracking, basic text coach, 7-day history |
| Plus | $9.99/mo | Unlimited chat, voice coaching, habit tracking, AI journaling, 30-day history |
| Pro | $24.99/mo | Unlimited Knowledge Brain, Learning/Fitness/Career coaches, advanced insights, 90-day history |
| Elite | $49.99/mo | Multi-agent orchestration, long-term memory, burnout prediction, family accounts, priority support |
| Enterprise | Custom | White-label, SSO, admin console, SLA, on-prem options |

---

## 11. Success Metrics (KPIs)

- **DAU/MAU** ≥ 30% (paid users within 12 months)
- **30-day churn** < 5% (Pro/Elite)
- **NPS** ≥ 55 within 6 months
- **Engagement** ≥ 3 AI interactions/day per active user
- **Goal completion** ≥ 40% of goals achieved within target windows
- **Revenue** $5 M ARR by end of Year 2; $20 M ARR by Year 4
- **Quality** — 0 cross-tenant isolation defects; ≥ 99.9% measured uptime after R2

---

## 12. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM provider rate limits | Medium | High | Multi-provider fallback (Groq → Gemini), batching, reserved capacity |
| Data privacy breach | Low | Critical | Tenant isolation (tested), encryption at rest/in transit, regular audits |
| Hallucination in sensitive domains (mental health, finance) | Medium | High | Safety layer, grounding via RAG, crisis escalation, human-in-the-loop; agents are coaches, **not** therapists/diagnostic or investment tools |
| Adoption vs. fragmentation | Medium | High | Strong onboarding, unified UI, migration utilities |
| GDPR/CCPA non-compliance | Low | Critical | Data-subject request APIs (R1), compliance event audit trail, audits |

---

## 13. Out of Scope / Non-Goals

- Medical diagnosis or therapy replacement (Mental Wellness Coach is CBT/positive-psychology *inspired* only)
- Investment or financial advice (Financial Coach = spending awareness, saving goals, habits)
- Native mobile apps in R1–R2 (web-first; React Native/Expo evaluated post-R3)
- On-device inference before R4

---

*Prepared by the Lumenly Product & Architecture Team — 2026-10-17. Aligned with `docs/product/requirements.md`, `docs/architecture/system-architecture.md`, and `docs/Roadmap.md`.*
