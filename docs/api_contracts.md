---
title: Lumenly API Contracts

# Lumenly – Production-Grade API Specification

_Version: v1.0 (2026-06-19) – Designed for 10M+ active users_

---

## 1. API Overview & Philosophy

**Aspect** | **Decision**
-----------|-----------
Style | RESTful, resource-oriented, stateless. All side-effects are expressed via standard HTTP verbs.
Versioning | URI versioning: /v1/... Future major versions use /v2/...
Naming | Plural kebab-case nouns (/users, /goals). Action-oriented endpoints (/reset-password) are kept verb-oriented under a resource root.
Response Envelope | Every successful response follows: {success: true, data: {...}, meta: {requestId, timestamp}, links: {self, next, prev}}.
Error Envelope | Failed responses use: {success: false, error: {code: "VALIDATION_ERROR", message: "..."} }.
Rate Limiting | Tier-based limits (Free: 60/min, Plus: 300/min, Pro: 1200/min, Enterprise: custom). Headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, Retry-After.
Security | All endpoints require JWT Bearer token except public auth endpoints. RBAC scopes enforce access to sensitive routes.

---

## 2. Global Standards

### 2.1 OpenAPI Component Schemas (abstract)

Note – All schemas are reusable via $ref. Only a subset is shown; the full OpenAPI file lives at docs/openapi.yaml.

```yaml
components:
  schemas:
    UUID:
      type: string
      format: uuid
      example: "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    ISO8601:
      type: string
      format: date-time
      example: "2026-06-19T12:34:56Z"
    PaginationMeta:
      type: object
      properties:
        requestId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
      required: [requestId, timestamp]
    ErrorDetail:
      type: object
      additionalProperties: true
    ErrorResponse:
      type: object
      required: [success, error, meta]
      properties:
        success:
          type: boolean
          enum: [false]
        error:
          type: object
          required: [code, message]
          properties:
            code:
              type: string
            message:
              type: string
            details:
              $ref: '#/components/schemas/ErrorDetail'
        meta:
          $ref: '#/components/schemas/MetadataBase'
    MetaBase:
      type: object
      properties:
        requestId:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
```

### 2.2 Global Parameters

| Parameter | In | Type | Required | Description |
|-----------|----|------|----------|-------------|
| Authorization | header | string | Yes (except auth endpoints) | Bearer JWT token |
| Idempotency-Key | header | string (UUID) | No (required for POST/PATCH that create/modify resources) | Guarantees exactly-once execution |
| Accept | header | string | No | application/json (default) |
| Content-Type | header | string | Yes (for request bodies) | application/json or multipart/form-data |
| Limit | query | integer | No | Page size (max 100) |
| Cursor | query | string | No | Opaque token for pagination |
| SortBy | query | string | No | Field name to sort |
| Order | query | string | No | asc or desc |

### 2.3 Error Code Catalog

| Code | HTTP Status | Meaning | When to Use |
|------|-------------|---------|-------------|
| VALIDATION_ERROR | 400 | Request body or parameters fail schema validation | Input Sanitization |
| AUTHENTICATION_FAILED | 401 | Missing or invalid JWT | Authorization Layer |
| AUTHORIZATION_REQUIRED | 403 | Authenticated but lacks required RBAC scope | Access Control |
| RESOURCE_NOT_FOUND | 404 | Target resource does not exist | CRUD Operations |
| CONFLICT | 409 | Resource state conflict (e.g., duplicate email) | Idempotency Conflicts |
| RATE_LIMIT_EXCEEDED | 429 | Caller exceeded tier quota | Rate Limiting |
| TOO_MANY_REQUESTS | 429 | Same as above – kept for semantic clarity | Rate Limiting |
| INTERNAL_ERROR | 500 | Unexpected server-side failure | Fallback |
| SERVICE_UNAVAILABLE | 503 | Temporary unavailability (planned maintenance) | Maintenance Windows |
| DEPRECATED_ENDPOINT | 410 | Endpoint removed; client should migrate | Deprecation |

### 2.4 Rate Limit Specification

- Headers returned on every response:
  - X-RateLimit-Limit: <max>
  - X-RateLimit-Remaining: <remaining>
  - X-RateLimit-Reset: <unix-timestamp>
  - Retry-After: <seconds> (on 429 responses)
- Token bucket algorithm: refill per minute; burst up to 2x limit.
- Enterprise tier receives custom quota negotiated per contract.

---

## 3. Authentication & Authorization

### 3.1 JWT Details

| Claim | Type | Description |
|-------|------|-------------|
| sub | string (UUID) | User ID |
| aud | string | Audience – lumenly-api |
| iss | string | Issuer – auth.lumenly.com |
| iat | number | Issued-at (seconds) |
| exp | number | Expiration (15 minutes) |
| scp | array[string] | Scopes (e.g., user:read, coach:write) |
| org | string (optional) | Organization ID for Enterprise users |

Signing – RSA-256 with 4096-bit key, rotated weekly. Public keys served via JWKS endpoint: GET /v1/auth/.well-known/jwks.json.

### 3.2 Refresh-Token Flow

1. Login → returns accessToken (15 min) + refreshToken (30 days).
2. Refresh → validates refresh token, rotates both tokens (rotation pattern).
3. Logout → revokes refresh token (store in deny-list).
4. Password reset flow: send reset link → user creates new password → rotates tokens.

### 3.3 RBAC Permissions Matrix

| Role | Example Scopes | Authorized Endpoints |
|------|----------------|----------------------|
| User | user:read, user:update, profile:_update | /v1/users/me, /v1/profiles/me |
| Coach | coach:read, coach:write, conversation:write | /v1/coaching/* |
| Admin | admin:_ (full) | /v1/admin/* |
| System | system:_ (full) | Internal service‑to‑service calls |

Scope checking occurs in **Authorization Middleware** before request handling.

---

## 4. Endpoints (by functional domain)

### 4.1 Authentication APIs

#### POST /v1/auth/register
- **Purpose**: Create new user account
- **Request Schema**: `RegisterRequest` (email, password, name)
- **Response**: `AuthResponse` (userId, accessToken, refreshToken)
- **Validation**: email RFC‑5322, password ≥12 chars with strength requirements
- **Rate Limit**: 10/min per IP
- **Error Codes**: VALIDATION_ERROR, CONFLICT

#### POST /v1/auth/login
- **Purpose**: Issue access & refresh tokens
- **Request**: `LoginRequest` (email, password)
- **Response**: `AuthResponse`
- **Rate Limit**: 30/min per IP
- **Error Codes**: AUTHENTICATION_FAILED

*(Additional auth endpoints: logout, forgot-password, reset-password, verify-email, change-password - follow same pattern with appropriate request/response schemas and validations.)*

### 4.2 User APIs

#### GET /v1/users/me
- **Purpose**: Retrieve own account details
- **Response**: `UserResponse`
- **Rate Limit**: 120/min per token

#### PATCH /v1/users/me
- **Purpose**: Update mutable profile fields
- **Request**: `UserUpdateRequest` (partial fields)
- **Response**: `UserResponse`
- **Validation**: email uniqueness, name length 1‑100
- **Rate Limit**: 60/min

#### DELETE /v1/users/me
- **Purpose**: Soft-delete account
- **Response**: `{success: true, data: {message}}`
- **Rate Limit**: 5/min

*(Additional endpoints: /v1/users/:id – admin only)*

### 4.3 Profile APIs

#### GET /v1/profiles/me
- **Purpose**: Retrieve enriched profile
- **Response**: `ProfileResponse`
- **Rate Limit**: 120/min

#### PATCH /v1/profiles/me
- **Purpose**: Partial update (age, domains, prefs)
- **Request**: `ProfileUpdateRequest`
- **Response**: `ProfileResponse`
- **Validation**: age 0‑120, lifeDomains enum, communicationStyle enum
- **Rate Limit**: 60/min

### 4.4 Conversation & Message APIs

#### POST /v1/conversations
- **Purpose**: Initiate new conversation
- **Request**: `ConversationCreateRequest` (title, participants[])
- **Response**: `ConversationResponse` (id, createdAt)
- **Validation**: participants must be valid agent IDs
- **Rate Limit**: 60/min

#### GET /v1/conversations
- **Purpose**: List conversations (cursor pagination)
- **Response**: `ConversationListResponse`
- **Rate Limit**: 120/min

#### GET /v1/conversations/{conversationId}
- **Purpose**: Retrieve metadata + participants
- **Response**: `ConversationDetailResponse`
- **Rate Limit**: 200/min

#### POST /v1/messages
- **Purpose**: Append message to conversation
- **Request**: `MessageCreateRequest` (conversationId, role, content, metadata)
- **Response**: `MessageResponse` (id, sentAt)
- **Validation**: role enum, payload size ≤2MB for voice
- **Rate Limit**: 300/min

#### GET /v1/messages
- **Purpose**: List messages for a conversation
- **Response**: `MessageListResponse`
- **Rate Limit**: 300/min

*(Additional endpoints: /v1/messages/{messageId}, DELETE /v1/conversations/{id} – soft delete.)*

### 4.5 Memory Engine APIs

#### GET /v1/memory
- **Purpose**: List memory entries (filter by type, tags, limit, cursor)
- **Response**: `MemoryListResponse`
- **Rate Limit**: 200/min

#### GET /v1/memory/{id}
- **Purpose**: Retrieve specific memory entry
- **Response**: `MemoryDetailResponse`
- **Rate Limit**: 200/min

#### POST /v1/memory
- **Purpose**: Create new memory record
- **Request**: `MemoryCreateRequest` (title, content, type, tags)
- **Response**: `MemoryDetailResponse` (new id)
- **Rate Limit**: 60/min

#### PATCH /v1/memory/{id}
- **Purpose**: Update memory partially
- **Request**: `MemoryUpdateRequest`
- **Response**: `MemoryDetailResponse`
- **Rate Limit**: 60/min

#### DELETE /v1/memory/{id}
- **Purpose**: Soft-delete memory
- **Response**: `{success: true}`
- **Rate Limit**: 30/min

### 4.6 Journal APIs

#### POST /v1/journal
- **Purpose**: Create new journal entry
- **Request**: `JournalCreateRequest` (title, body, optional moodId, tags)
- **Response**: `JournalDetailResponse`
- **Validation**: title 1‑150 chars, body ≤50KB, tags ≤5 items
- **Rate Limit**: 120/min

#### GET /v1/journal
- **Purpose**: List entries with filters (date range, tags, moodId)
- **Response**: `JournalListResponse`
- **Rate Limit**: 200/min

*(Additional endpoints: GET /v1/journal/{id}, PATCH /v1/journal/{id}, DELETE /v1/journal/{id})*

### 4.7 Mood Tracking APIs

#### POST /v1/moods
- **Purpose**: Record mood snapshot
- **Request**: `MoodCreateRequest` (mood enum, intensity 1‑10, optional note)
- **Response**: `MoodDetailResponse`
- **Validation**: intensity 1‑10
- **Rate Limit**: 120/min

#### GET /v1/moods
- **Purpose**: List mood entries with filters
- **Response**: `MoodListResponse`
- **Rate Limit**: 200/min

#### GET /v1/moods/trends
- **Purpose**: Aggregated mood trends
- **Response**: `MoodTrendsResponse`
- **Rate Limit**: 60/min

*(Additional endpoint: DELETE /v1/moods/{id} – soft delete.)*

### 4.8 Goals APIs

#### POST /v1/goals
- **Purpose**: Create SMART goal
- **Request**: `GoalCreateRequest` (title, description, targetDate, pillar, progress, status)
- **Response**: `GoalDetailResponse`
- **Validation**: title 1‑150 chars, targetDate future, status enum
- **Rate Limit**: 60/min

#### GET /v1/goals
- **Purpose**: List goals (filter by status, tags)
- **Response**: `GoalListResponse`
- **Rate Limit**: 200/min

#### GET /v1/goals/{id}
- **Purpose**: Retrieve specific goal
- **Response**: `GoalDetailResponse`
- **Rate Limit**: 200/min

#### PATCH /v1/goals/{id}
- **Purpose**: Update goal mutable fields
- **Response**: `GoalDetailResponse`
- **Rate Limit**: 60/min

#### DELETE /v1/goals/{id}
- **Purpose**: Archive/delete goal
- **Response**: `{success: true}`
- **Rate Limit**: 30/min

*(Additional endpoints: milestone tracking, related habit linking.)*

### 4.9 Habit APIs

#### POST /v1/habits
- **Request**: `HabitCreateRequest` (name, pillar, frequency, reminderTime)
- **Response**: `HabitDetailResponse`
- **Rate Limit**: 60/min

#### GET /v1/habits
- **Response**: `HabitListResponse`
- **Rate Limit**: 200/min

#### GET /v1/habits/{id}
- **Response**: `HabitDetailResponse`
- **Rate Limit**: 200/min

#### PATCH /v1/habits/{id}
- **Response**: `HabitDetailResponse`
- **Rate Limit**: 60/min

#### POST /v1/habits/{id}/check-in
- **Purpose**: Record habit check-in
- **Response**: `{success: true, data: {checkedAt}}`
- **Rate Limit**: 120/min

### 4.10 Coaching APIs

#### POST /v1/coaching/session
- **Purpose**: Start multi-agent coaching session
- **Request**: `CoachingSessionRequest` (agent enum, contextIds[], parameters)
- **Response**: `CoachingSessionResponse` (sessionId, websocketUrl)
- **Validation**: agent must be defined, contextIds must exist
- **Rate Limit**: 30/min
- **WebSocket**: /v1/coaching/ws/{sessionId} – message types: assistant_message, tool_call, tool_response, error, heartbeat

#### GET /v1/coaching/history
- **Response**: `CoachingHistoryResponse`
- **Rate Limit**: 120/min

#### GET /v1/coaching/insights
- **Response**: `CoachingInsightsResponse`
- **Rate Limit**: 60/min

### 4.11 Knowledge Brain APIs

#### POST /v1/knowledge/upload
- **Purpose**: Upload PDF/book/notes
- **Request**: multipart/form-data (file ≤50MB, type enum, optional metadata)
- **Response**: `KnowledgeUploadResponse` (documentId, ingestStatusUrl)
- **Validation**: MIME type, file size
- **Rate Limit**: 20/min

#### GET /v1/knowledge/documents
- **Response**: `KnowledgeListResponse`
- **Rate Limit**: 200/min

#### GET /v1/knowledge/documents/{id}
- **Response**: `KnowledgeDetailResponse` or binary stream
- **Rate Limit**: 100/min (metadata), 20/min (download)

#### DELETE /v1/knowledge/documents/{id}
- **Purpose**: Soft-delete document
- **Response**: `{success: true}`
- **Rate Limit**: 30/min

#### POST /v1/rag/query
- **Purpose**: Retrieval-Augmented Generation
- **Request**: `RagQueryRequest` (query, topK, optional filters)
- **Response**: `RagQueryResponse` (answer, sourceDocuments[], latencyMs)
- **Validation**: topK 1‑20, query ≤500 chars
- **Rate Limit**: 60/min

#### POST /v1/rag/reindex
- **Purpose**: Trigger full/partial index rebuild (admin)
- **Request**: `RagReindexRequest` (documentIds[] optional)
- **Response**: `TaskResponse` (taskId)
- **Rate Limit**: 5/min
- **Security**: admin scope required

#### GET /v1/rag/status
- **Purpose**: Check status of last re-index job
- **Response**: `RagStatusResponse`
- **Rate Limit**: 30/min

### 4.12 Wellness APIs

#### GET /v1/wellness/dashboard
- **Response**: `WellnessDashboardResponse` (composite view)
- **Rate Limit**: 60/min

#### GET /v1/wellness/score
- **Response**: `{success: true, data: {overall: 0‑100, components: {mood: 0‑10, ...}}}`
- **Rate Limit**: 60/min

#### GET /v1/wellness/trends
- **Response**: `WellnessTrendsResponse`
- **Rate Limit**: 60/min

#### GET /v1/wellness/recommendations
- **Response**: `WellnessRecommendationsResponse`
- **Rate Limit**: 30/min

### 4.13 Voice APIs

#### POST /v1/voice/transcribe
- **Purpose**: Speech-to-text
- **Request**: multipart audio (wav, mp3 ≤5MB)
- **Response**: `TranscribeResponse` (text)
- **Rate Limit**: 30/min

#### POST /v1/voice/synthesize
- **Purpose**: Text-to-speech
- **Request**: VoiceSynthesizeRequest (text ≤2KB, voice name, style enum)
- **Response**: `VoiceSynthesizeResponse` (audioUrl, durationMs)
- **Rate Limit**: 20/min

#### POST /v1/voice/chat
- **Purpose**: Bidirectional voice chat bootstrap
- **Request**: VoiceChatRequest (sessionId?, agent, audioChunk base64)
- **Response**: VoiceChatResponse (audioChunk base64, nextSessionId?)
- **Rate Limit**: 10 msg/s via WebSocket

### 4.14 AI Insights APIs

#### GET /v1/insights
- **Response**: `InsightsCatalogResponse` (array of {type, title, description})
- **Rate Limit**: 60/min

#### GET /v1/insights/daily
- **Response**: `InsightListResponse` (daily snapshot)
- **Rate Limit**: 120/min

*(continued with weekly/monthly endpoints – same pattern)*

### 4.15 Subscription APIs

#### GET /v1/subscription
- **Response**: `SubscriptionResponse` (current plan, renewal date)
- **Rate Limit**: 60/min

#### POST /v1/subscription/upgrade
- **Request**: `UpgradeRequest` (plan enum)
- **Response**: `SubscriptionResponse` (new plan)
- **Validation**: plan must be higher than current
- **Rate Limit**: 30/min

#### POST /v1/subscription/cancel
- **Response**: `{success: true, data: {effectiveDate}}`
- **Rate Limit**: 30/min

### 4.16 Webhook APIs

#### POST /webhooks/stripe
- **Purpose**: Stripe event notifications
- **Security**: Verify Stripe-Signature header
- **Response**: 200 OK on success
- **Rate Limit**: N/A

*(additional webhook endpoints: /webhooks/email, /webhooks/notifications)*

---

## 5. Mermaid Flow Diagrams

*(Mermaid diagrams illustrating authentication flow, conversation flow, coaching flow, memory retrieval flow, voice conversation flow – referenced but not reproduced in full here.)*

---

## 6. Event Bus Schemas

*(JSON Schema examples for UserCreated, GoalCreated, HabitCompleted, MemoryUpdated, CoachingCompleted, DocumentUploaded, RagReindexFinished, SubscriptionChanged – as defined in system architecture document.)*

---

## 7. Appendices

### 7.1 Pagination Contract

- Cursor is opaque Base64 encoding of (lastSortedField, _id) pair.
- Forward pagination: `WHERE _id > cursor_value ORDER BY _id ASC`.
- Backward pagination: `WHERE _id < cursor_value ORDER BY _id DESC`.

### 7.2 Filtering Contract

- Operators: `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`, `$in`, `$nin`, `$contains`.
- Example: `GET /v1/goals?filter={"status":"active","tags":["health"]}`

### 7.3 Sorting Contract

- `sortBy` must be whitelisted per resource.
- `order` defaults to `asc`.

### 7.4 Validation Rule Cheat Sheet

| Field | Rule | Example |
|-------|------|---------|
| email | RFC‑5322, unique | user@example.com |
| password | ≥12 chars, ≥1 upper, ≥1 lower, ≥1 digit, ≥1 special | Str0ng!Passw0rd |
| name | 1‑100 unicode chars | "Ada Lovelace" |
| title | 1‑150 chars | "Run a marathon" |
| tags | ≤10 items, ≤30 chars each | ["health","fitness"] |
| mood.intensity | 1‑10 integer | 7 |
| habit.frequency | enum daily|weekly|monthly|custom | daily |
| voice.audioChunk | Base64, ≤1MB | — |

### 7.5 OpenAPI Snippet (YAML)

```yaml
paths:
  /v1/auth/login:
    post:
      summary: Issue access & refresh tokens
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/LoginRequest'
      responses:
        '200':
          description: Successful authentication
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AuthResponse'
        '401':
          description: Invalid credentials
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
```

---

*Prepared for internal engineering use. Version 1.0 – 2026-06-19.*