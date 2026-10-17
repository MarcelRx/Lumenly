---
title: Lumenly — Final Product Requirements Document (PRD)
author: Lumenly Product & Engineering Team
date: 2026-10-17
version: 2.0
status: FINAL — PRODUCTION
supersedes: PRD v1.1 (2026-06-23)
---

# Lumenly — Final Production PRD (v2.0)

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Vision, Mission & Product Philosophy](#2-vision-mission--product-philosophy)
3. [Market Opportunity](#3-market-opportunity)
4. [User Personas](#4-user-personas)
5. [Problem Statement](#5-problem-statement)
6. [Product Positioning](#6-product-positioning)
7. [Functional Requirements](#7-functional-requirements)
8. [Non-Functional Requirements](#8-non-functional-requirements)
9. [System, Data & API Requirements](#9-system-data--api-requirements)
10. [Safety, Privacy & Compliance](#10-safety-privacy--compliance)
11. [Monetization Strategy](#11-monetization-strategy)
12. [Success Metrics (KPIs)](#12-success-metrics-kpis)
13. [Release Plan](#13-release-plan)
14. [Risks & Mitigations](#14-risks--mitigations)
15. [Out of Scope](#15-out-of-scope)
16. [Open Questions](#16-open-questions)
17. [Appendix: Requirements Traceability](#17-appendix-requirements-traceability)

---

## 1. Executive Summary

Lumenly is an **AI-native Life Operating System** that consolidates ten personal-development domains — mental health, emotional intelligence, productivity, learning, habit formation, physical fitness, relationships, career growth, financial discipline, and life-goal management — into a single, conversational AI companion.

Instead of five fragmented apps (meditation, habits, fitness, productivity, journaling), the user has **one AI that understands their entire life**. Lumenly unifies data across domains to deliver proactive, personalized coaching that adapts to each user's unique context, producing sustained, measurable improvement in every major area of life.

**One-sentence pitch:** *Lumenly is an AI Life Operating System that combines long-term memory, personal knowledge, behavioral analytics, and specialized coaching agents to help people continuously improve every major area of their lives through one unified AI companion.*

This document is the single, authoritative product specification for production. It consolidates and supersedes: PRD v1.1, `project_idea.text`, and the product-facing content of `system_architecture.md`, `ai_system_design.md`, `database_design.md`, and `api_contracts.md`.

---

## 2. Vision, Mission & Product Philosophy

- **Vision:** Become the single AI companion that *knows* a user's entire life story and continuously guides them toward their highest-potential self.
- **Mission:** Create a unified, privacy-first AI platform that **learns**, **remembers**, and **guides** users toward their optimal selves through personalized, cross-domain insights and actionable coaching.

**Product Philosophy**

Most AI apps answer questions. Lumenly answers:

- *Why are you struggling?*
- *What should you do next?*
- *What action will create the biggest improvement?*
- *What patterns are holding you back?*

---

## 3. Market Opportunity

| Segment | TAM (2025) | SAM (2026) | SOM (3-yr) |
|---------|-----------:|-----------:|-----------:|
| Self-Improvement & Wellness Apps | $180 B | $45 B | $540 M |
| Productivity & Task Management | $60 B | $12 B | $144 M |
| Digital Coaching & Therapy | $30 B | $6 B | $72 M |
| **Combined Addressable Market** | **$270 B** | **$63 B** | **$756 M** |

Approximately 30% of users in these segments express willingness to pay $10–$25/month for an integrated, AI-driven experience that eliminates app fragmentation and delivers context-aware guidance.

---

## 4. User Personas

| # | Persona | Age | Occupation | Core Pain Points | Desired Outcomes |
|---|---------|-----|------------|------------------|------------------|
| 1 | Growth-Focused Professional | 28–38 | Software Engineer, PM | Multiple apps, limited reflection time | Unified daily check-in, data-driven habit loops |
| 2 | Wellness-First Urbanite | 30–45 | Marketing, Consulting | Inconsistent fitness & mental-health tracking | Holistic health score, guided meditations |
| 3 | Aspiring Entrepreneur | 25–35 | Founder, Side-Hustler | Overwhelmed by goal-setting frameworks | AI-crafted roadmap, milestone tracking |
| 4 | Life-Transition Seeker | 40–55 | Mid-career professional | Lack of purpose after major life change | Structured reflection, career-pivot planning |
| 5 | Financially-Savvy Saver | 30–50 | Analyst, Freelancer | Scattered budgeting tools | Integrated discipline, goal-linked saving |

---

## 5. Problem Statement

| # | Problem | Impact |
|---|---------|--------|
| P1 | **Fragmentation** — users juggle 5+ separate apps | Data silos, low adherence |
| P2 | **Context-switch overhead** | Reduced focus; diminished intervention impact |
| P3 | **Generic advice** — one-size-fits-all recommendations | Ignores personal context; low trust |
| P4 | **Memory decay** — insights from previous sessions are lost | No persistent, cross-domain memory |
| P5 | **Motivation fatigue** — sparse, isolated nudges | Effectiveness declines over time |
| P6 | **Privacy concerns** — centralized personal data | Trust barrier without clear controls |

---

## 6. Product Positioning

> **Lumenly is not a chatbot, meditation app, or habit tracker.**
> **Lumenly is the AI Operating System for Human Growth.**

It delivers a single, continuously learning companion that:

- **Remembers** every interaction across all life domains (Memory Engine).
- **Synthesizes** cross-domain signals into actionable recommendations (Wellness Intelligence).
- **Coaches** users in real time — text and voice — in a tone that feels personal, supportive, and evidence-based (8 specialized agents + Fusion Engine).

**Core Product Layers (production scope):**

1. **User Data Layer** — manual inputs (journals, mood check-ins, goals, habits, reflections, tasks), connected data (Apple Health, Google Fit, Fitbit, Garmin, Oura, Calendar, Notion, Todoist — phased), uploaded knowledge (books, PDFs, research papers, notes).
2. **Memory System** — working, episodic, semantic, goal, and procedural memory; the most important system in the product.
3. **Knowledge Brain** — user-uploaded content becomes grounded, personalized coaching (the differentiator).
4. **Life Intelligence Engine** — the AI brain: Wellness Score, predictive intelligence, and cross-domain recommendations.

---

## 7. Functional Requirements

Priorities: **P0** = production-blocking, **P1** = required for GA, **P2** = fast-follow, **P3** = later phases.

### FR-1 — Unified Dashboard

| Field | Value |
|---|---|
| Priority | **P0** |
| Description | Real-time view of Wellness Score, today's priorities, mood, and AI insights. Home surface of web and mobile apps. |
| Acceptance | Dashboard loads < 1.5 s (p95); score, priorities, mood, and top 3 insights render in one composite API call (`GET /v1/wellness/dashboard`). |

### FR-2 — Conversational AI Coach (8 Agents + Fusion Engine)

| Field | Value |
|---|---|
| Priority | **P0** |
| Description | Eight specialized agents collaborate via the Fusion Engine: Life Strategist (master coordinator), Mental Wellness Coach (CBT/positive-psychology inspired; not a therapist), Habit Coach (Tiny Habits, Habit Loop, identity-based habits), Learning Coach (summaries, quizzes, study plans, spaced repetition), Fitness Coach (workout/recovery plans), Career Coach (skills, planning, interview prep), Financial Coach (spending awareness, saving goals; not investment advice), Relationship Coach (communication, emotional intelligence, conflict resolution). |
| Acceptance | Intent classification routes to correct agent with ≥ 95% routing accuracy on the golden test set; multi-domain queries trigger ≥ 2 agents and Fusion resolves conflicts via the safety priority matrix (Mental Wellness > others in crisis scenarios); every response carries a `prompt_version_id` for traceability. |

### FR-3 — Voice Companion ("Lumen")

| Field | Value |
|---|---|
| Priority | **P1** |
| Description | Always-on audio persona: natural conversations, real-time coaching, voice journaling, emotional tone detection. STT/TTS via ElevenLabs; fast inference via Groq. |
| Acceptance | Voice round-trip (end of speech → start of audio playback) < 1.5 s (p95); synthesized audio cached in Redis (5-min TTL) and served via signed URL; TTS failure degrades gracefully to text-only response. |

### FR-4 — Cross-Domain Memory Graph

| Field | Value |
|---|---|
| Priority | **P0** |
| Description | Privacy-first persistent memory: Working (session context, ~2k tokens, Redis), Episodic (conversations/messages in MongoDB), Semantic (vectors in Qdrant + metadata in `memory_links`), Goal memory (`goals` collection). Fusion scores by recency, relevance, and personalization weight; fallback to Knowledge Brain when fusion score < 0.3. |
| Acceptance | Lumenly recalls a user-stated preference (e.g., "studies best at night") in a later session without re-prompting; deletion of a user purges vectors from Qdrant, links from MongoDB, and caches from Redis within 24 h. |

### FR-5 — Personalized Goal Engine

| Field | Value |
|---|---|
| Priority | **P0** |
| Description | SMART goal creation, milestone decomposition, adaptive progress tracking, related-habit linking. |
| Acceptance | Goal CRUD via `/v1/goals`; milestones embed inside goals; progress recomputes on milestone/habit events; statuses: `active`, `completed`, `canceled`, `paused`. |

### FR-6 — Habit Loop Builder

| Field | Value |
|---|---|
| Priority | **P0** |
| Description | Cue–routine–reward loops auto-suggested from behavioral-science frameworks (Tiny Habits, identity-based habits); streak tracking; daily check-ins. |
| Acceptance | Habit CRUD + check-in via `/v1/habits`; current/longest streaks computed correctly; `HabitCompleted` events feed the Personalization Engine. |

### FR-7 — Knowledge Brain (RAG)

| Field | Value |
|---|---|
| Priority | **P1** |
| Description | Upload PDFs/books/notes (≤ 50 MB); async ingestion pipeline: chunking (1k-token window, 200-token stride) → embeddings → Qdrant upsert → `memory_links` metadata → hybrid retrieval (ANN + BM25 re-rank, LLM re-ranker on top-20). Coaching answers must be grounded in the user's own material. |
| Acceptance | e.g., "Based on *Deep Work*, schedule focus sessions 8–10 PM — historically this raises your task completion by ~31%"; ingestion status observable; admin re-index supported; `nDCG@10` tracked daily. |

### FR-8 — Wellness Intelligence Engine

| Field | Value |
|---|---|
| Priority | **P0** |
| Description | Proprietary 0–100 Wellness Score aggregating manual inputs and (phased) wearables via Redis streams + Celery analytics workers. |

| Area | Weight |
|---|---|
| Sleep | 20% |
| Mood | 20% |
| Productivity | 15% |
| Habits | 15% |
| Fitness | 10% |
| Learning | 10% |
| Relationships | 10% |

**Acceptance:** score recomputed daily and on new signals; history retained in `profiles.scoreHistory`; dashboard surfaces the main improvement opportunity (e.g., "Sleep consistency").

### FR-9 — Predictive Intelligence

| Field | Value |
|---|---|
| Priority | **P2** |
| Description | Early warnings — computed before events occur — for burnout risk, motivation decline, habit-failure risk, stress escalation, and goal abandonment, with proactive recommendations (e.g., "Your burnout risk increased 24% this week due to decreased sleep and increased workload"). |
| Acceptance | Risk alerts surface as `ai_insights` of type `burnout_warning` / `risk_alert` with correlation payloads; alert precision reviewed weekly before graduating from beta. |

### FR-10 — Challenges System

| Field | Value |
|---|---|
| Priority | **P2** |
| Description | Dynamically generated 7-day / 30-day / custom sprints (Focus Sprint, Habit Builder, Morning Routine, Deep Work, Confidence Challenge) bundling related goals, habits, and tasks. |
| Acceptance | Challenge lifecycle (active → completed/abandoned) tracked in `wellness_challenges`; progress recomputed daily. |

### FR-11 — Personalization Engine

| Field | Value |
|---|---|
| Priority | **P1** |
| Description | Computes a User Blueprint (tone, depth, domain priorities) from goal completion rates, habit adherence, and interaction sentiment; refreshed on `HabitCompleted` / `GoalUpdated` events; cached in Redis (1-h TTL). |
| Acceptance | Blueprint changes are reflected in agent tone within one session of the triggering event. |

### FR-12 — Privacy-First Architecture

| Field | Value |
|---|---|
| Priority | **P0** |
| Description | Encryption at rest (AES-256-GCM), deterministic tokenization of identifiers before vector storage (no PII in Qdrant), granular consent controls, optional on-device inference, GDPR/CCPA compliance. |
| Acceptance | `/forget` endpoint triggers full data purge within 24 h; soft-delete TTLs enforced (journal 180 d, insights 90 d, conversations 365 d). |

### FR-13 — Subscriptions & Billing

| Field | Value |
|---|---|
| Priority | **P1** |
| Description | Tier management via Stripe (Free, Plus, Pro, Elite, Enterprise); webhooks with signature verification; audit-grade billing logs in PostgreSQL. |
| Acceptance | Plan upgrade/downgrade/cancel take effect per tier rules; `SubscriptionChanged` events emitted on the internal event bus. |

---

## 8. Non-Functional Requirements

| ID | Category | Requirement | Target |
|---|---|---|---|
| NFR-1 | Scale | Support 10M active users | Horizontal scaling: FastAPI workers, Redis cluster, Qdrant sharding, MongoDB shard key `hashed(userId)` |
| NFR-2 | Performance | Coaching response latency | Text: < 2 s p95 to first token; Voice: < 1.5 s p95 round-trip; voice-path inference < 500 ms (Groq) |
| NFR-3 | Availability | Platform uptime | ≥ 99.9% monthly; graceful degradation on every external dependency (LLM, Qdrant, Redis, ElevenLabs) |
| NFR-4 | Resilience | Failure recovery | LLM timeout → fallback model; Qdrant down → Redis-cached vectors + background re-index; ElevenLabs 5xx → text-only; worker crash → supervisor restart + event replay from Redis stream |
| NFR-5 | Cost | LLM spend control | Cost-aware routing (Groq primary ~$0.0002/1k, Gemini premium ~$0.0004/1k), batch embeddings (≤ 32 chunks), cache-first retrieval, per-user/per-tenant token budgets with auto-downgrade on overrun |
| NFR-6 | Security | AuthN/AuthZ | JWT RS-256 (4096-bit, weekly rotation, JWKS endpoint); access 15 min / refresh 30 d with rotation; RBAC scopes; rate limits per tier (Free 60/min → Enterprise custom) |
| NFR-7 | Observability | Metrics & alerting | Prometheus + Grafana + ELK; alert on latency, error rate, token cost; `model_calls`, `tokens_used`, `embedding_calls` instrumented |
| NFR-8 | Testability | Coverage | Unit, integration, e2e, contract, performance (Locust/Artillery), security (OWASP ZAP) suites required in CI before release |
| NFR-9 | Data retention | GDPR purges | TTL indexes on soft-deleted data; audit logs retained immutably in PostgreSQL |
| NFR-10 | Throughput | Coaching sessions | WebSocket sessions at 10 msg/s sustained; per-user rate limit 5 RPS on AI endpoints |

---

## 9. System, Data & API Requirements

**Reference architecture** (details live in the technical docs; PRD is the product authority):

| Component | Technology | Function |
|---|---|---|
| Backend | FastAPI (async, Python ≥ 3.11), Beanie/Motor ODM | REST + WebSocket, auth, rate limiting, orchestration |
| Primary store | MongoDB Atlas (globally replicated) | All mutable user data; flat, SQL-compatible schemas |
| Vector store | Qdrant | Semantic embeddings for RAG + memory (exclusively; no pgvector) |
| Cache | Redis (cluster) | Sessions, working memory, rate limits, audio cache |
| Audit & billing | PostgreSQL | Immutable, ACID financial/compliance logs |
| LLM providers | Groq (primary/voice-fast), Gemini (premium/enterprise/long-context), Claude-Haiku (small-talk, re-ranking, safety classification) | Generation, embeddings, re-ranking |
| Voice | ElevenLabs STT/TTS | Real-time voice pipeline |
| Workers | Celery/Dramatiq | Embedding pipelines, analytics, nudges |
| Events | Kafka-compatible internal bus | `UserCreated`, `GoalCompleted`, `HabitCompleted`, `MemoryUpdated`, `SubscriptionChanged`, … |
| Infra | Docker, Kubernetes (Helm), Terraform, Nginx; CI/CD via GitHub Actions + Snyk | Deployment, scaling, security scanning |
| Admin/analytics | Atlas SQL Interface | ANSI-SQL over NoSQL for admin dashboards & compliance |

**Data entities (MongoDB):** `users`, `profiles` (embeds wellnessScore, personalizationBlueprint), `conversations` (embeds `messages`), `journal_entries`, `mood_entries`, `goals` (embeds milestones), `habits` (embeds check-ins), `ai_insights`, `documents`, `memory_links`, `wellness_challenges`, `subscriptions` — plus PostgreSQL `audit_log`.

**API surface:** 16 versioned endpoint groups under `/v1` — auth, users, profiles, conversations/messages, memory, journal, moods, goals, habits, coaching (REST + WebSocket), knowledge/rag, wellness, voice, insights, subscription, webhooks — using the standard success/error envelopes, cursor pagination, Idempotency-Key for mutating POST/PATCH, and the documented error-code catalog.

**Client:** React web (current) and React Native / Expo mobile (planned) — Home, AI Companion (chat + voice), Insights, Knowledge Brain, Goals, Habits, Learning, Fitness, Relationships, Profile.

---

## 10. Safety, Privacy & Compliance

| Guardrail | Mechanism |
|---|---|
| Crisis escalation | Sentiment < −0.8 + crisis keywords → emergency message, Mental Wellness agent priority, HIPAA-grade log |
| Medical disclaimer | Deterministic no-diagnosis rule set before any health response |
| Financial guardrail | Actionable investment suggestions capped at 5% of session output + mandatory disclaimer and user confirmation |
| Prompt-injection detection | Regex + Claude-Haiku classifier; rewrite suspicious prompts; log events |
| Toxicity detection | Self-hosted scorer; threshold 0.7 |
| Privacy | AES-256-GCM at rest; tokenized identifiers in Qdrant; `/forget` purge (MongoDB + Redis + Qdrant) within 24 h |
| Compliance | GDPR/CCPA data-subject request APIs; soft-delete + TTL purge policies; immutable PostgreSQL audit |

**Boundaries:** Lumenly is **not** a therapist, **not** a diagnostic system, and **not** an investment advisor. These boundaries are enforced, not merely stated.

---

## 11. Monetization Strategy

| Tier | Monthly Price | Core Features | Target Segment |
|------|--------------|---------------|----------------|
| Free | $0 | Daily check-ins, mood tracking, basic text AI coach, 7-day history | Exploration, low-commitment |
| Plus | $9.99 | Unlimited chat, voice coaching, habit tracking, AI journaling, 30-day history | Early adopters, casual self-improvers |
| Pro | $24.99 | Unlimited Knowledge Brain, Learning/Fitness/Career Coaches, advanced insights, 90-day history | Serious personal-development users |
| Elite | $49.99 | Multi-agent orchestration, long-term memory depth, burnout prediction, family accounts, executive coaching, priority support | Power users, professionals |
| Enterprise | Custom | White-label, SSO, dedicated admin console, SLA, on-prem deployment | Schools, universities, corporates, wellness programs |

---

## 12. Success Metrics (KPIs)

| Metric | Target |
|---|---|
| DAU/MAU (paid, within 12 mo) | ≥ 30% |
| 30-day churn (Pro/Elite) | < 5% |
| NPS (within 6 mo) | ≥ 55 |
| Engagement | ≥ 3 AI interactions/day per active user |
| Goal completion rate | ≥ 40% achieved within target windows |
| Retrieval quality (RAG) | nDCG@10 tracked daily; no regression > 5% between releases |
| Hallucination rate | Continuous self-verification; trending down release-over-release |
| Memory recall accuracy | Precision measured continuously via online logs |
| Coaching quality | Human-rated 1–5 (empathy, usefulness, personalization); weekly curator review |
| Revenue | $5 M ARR by end of Year 2; $20 M ARR by Year 4 |

---

## 13. Release Plan

Aligned with `docs/Roadmap.md`; production GA requires all **P0** requirements plus P1 Voice, Knowledge Brain, Personalization, and Subscriptions.

| Phase | Window | Milestones | Exit Criteria |
|-------|--------|------------|---------------|
| Phase 0 — Foundation | 0–2 mo | Repo, CI/CD, core API skeleton, Docker/K8s | **DONE** (see `PROJECT_MAP.md`) |
| Phase 1 — MVP | 2–6 mo | Auth, basic text AI coach, Memory Engine, Wellness Dashboard, Free tier | First paying users; P0 features in beta |
| Phase 2 — V1 (GA) | 6–12 mo | Voice companion, Goal Engine, Habit Builder, Knowledge Brain (PDF upload), subscriptions | All P0+P1 shipped; KPIs instrumented; 99.9% uptime |
| Phase 3 — V2 | 12–18 mo | Multi-agent orchestration at scale, Predictive Intelligence, Enterprise features, expanded wearables | Predictive alerts out of beta; Enterprise pilots |
| Phase 4 — Scale | 18–24 mo | Internationalization, AI content generation, advanced analytics, on-prem offering | Enterprise GA; ARR trajectory on track |

**Current status:** Phase 1 (MVP), ~20% complete — backend API skeleton and web login/chat UI working; `ai/`, `infra/`, and `tests/` modules are stubs pending implementation.

---

## 14. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM provider rate-limit constraints | Medium | High (service disruption) | Multi-provider fallback (Groq ↔ Gemini ↔ Haiku), batching, reserved capacity |
| Data privacy breach | Low | Critical | E2E encryption, zero-knowledge options, tokenized vectors, regular audits |
| User adoption vs. fragmentation inertia | Medium | High | Strong onboarding, migration utilities, unified UI/UX |
| Model hallucination in sensitive domains | Medium | High | Safety layer, crisis escalation, human-in-the-loop verification, self-verification agents |
| Regulatory non-compliance (GDPR/CCPA) | Low | Critical | Compliance ownership, regular audits, data-subject request APIs, 24-h purge SLA |
| Cost overrun on LLM spend | Medium | Medium | Cost-aware routing, per-user/tenant budgets, Prometheus cost alerting |
| Core AI modules still unbuilt (Memory, Knowledge Brain, Agents, Voice) | High | High | Critical path: Memory Engine → Knowledge Brain → Agent System → Voice; treat `ai/` as the product's heart, not a workstream |

---

## 15. Out of Scope

- Physical hardware or wearable manufacturing (integration only).
- Licensed therapy, medical diagnosis, or prescribed treatment.
- Regulated investment advice or tax filing.
- Social network features (feeds, following).
- Third-party marketplace for agents (may be revisited post-Phase 4).

---

## 16. Open Questions

| # | Question | Owner | Needed By |
|---|----------|-------|-----------|
| Q1 | Which embedding model is final (Groq `embed-3-large` vs. Gemini `embedding-v2` vs. open-source) — per tier or global? | AI Core | Phase 1 exit |
| Q2 | Wearable provider rollout order (Apple Health, Google Fit, Fitbit, Garmin, Oura)? | Product + Data | Phase 2 planning |
| Q3 | On-device inference: which use-cases and minimum device specs? | AI Core + Mobile | Phase 3 |
| Q4 | Enterprise SSO providers and on-prem packaging commitments? | Enterprise Sales + Platform | Phase 3 |
| Q5 | Family-account billing mechanics for Elite tier? | Product + Billing | Phase 3 |

---

## 17. Appendix: Requirements Traceability

| Requirement | Source document | Implementing docs |
|---|---|---|
| FR-1 Dashboard | PRD v1.1 §Core Features 1; project_idea (Mobile Application → Home) | api_contracts §4.12; database_design §2.2 |
| FR-2 Agents + Fusion | PRD v1.1 §Core Features 2; project_idea (AI Agents) | ai_system_design §3; project_structure §5.3/§8 |
| FR-3 Voice | PRD v1.1 §Core Features 2.1; project_idea (Voice Companion) | system_architecture §10; api_contracts §4.13 |
| FR-4 Memory Graph | PRD v1.1 §Core Features 3; project_idea (Layer 2) | ai_system_design §1; database_design §2.10 |
| FR-5 Goal Engine | PRD v1.1 §Core Features 4; project_idea (Agent 1) | database_design §2.5; api_contracts §4.8 |
| FR-6 Habit Builder | PRD v1.1 §Core Features 5; project_idea (Agent 3) | database_design §2.6; api_contracts §4.9 |
| FR-7 Knowledge Brain | PRD v1.1 §Core Features 6; project_idea (Layer 3) | ai_system_design §2; api_contracts §4.11 |
| FR-8 Wellness Score | PRD v1.1 §Core Features 7; project_idea (AI Wellness Score) | system_architecture §8; api_contracts §4.12 |
| FR-9 Predictive Intelligence | PRD v1.1 §Core Features 8; project_idea (Predictive Intelligence) | ai_system_design §7; PROJECT_MAP (wellness engine) |
| FR-10 Challenges | PRD v1.1 §Core Features 9; project_idea (Challenges System) | database_design §2.11 |
| FR-11 Personalization | system_architecture §7 | ai_system_design §3.3 |
| FR-12 Privacy | PRD v1.1 §Core Features 10 | ai_system_design §5; database_design §6 |
| FR-13 Subscriptions | PRD v1.1 §Monetization | database_design §2.12; api_contracts §4.15–4.16 |
| NFR-1–10 | system_architecture §13–§16; api_contracts §2 | system_architecture; database_design §5–§6 |

---

*Prepared by the Lumenly Product & Engineering Team — 2026-10-17. This PRD supersedes v1.1 (2026-06-23) in its entirety.*
