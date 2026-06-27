---
title: Lumenly – Database Design (MongoDB Atlas)
author: Lumenly Engineering Team
date: 2026-06-23
version: 1.2
---

# Lumenly — Database Design

---

## 1. Overview

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Primary Store** | **MongoDB Atlas** (document-oriented, globally replicated) | All user-centric data: identity, profile, conversations, journal, wellness scores, AI insights |
| **Cache / Session** | **Redis** (clustered) | Short-lived auth tokens, per-request state, rate-limit counters |
| **Vector Store** | **Qdrant** | Semantic embeddings for user memory & wellness vectors |
| **Transactional Audit** | **PostgreSQL** | Immutable billing & compliance logs requiring strict ACID guarantees |

> The backend queries MongoDB **via the Atlas SQL Interface**. All schemas are therefore kept flat, with predictable field types and minimal polymorphic arrays so that the Atlas SQL schema builder can infer a clean relational view.

---

## 2. MongoDB Collections & Schemas

> All `_id` fields are **ObjectId**. Timestamps use `ISODate`. Optional soft-delete uses a nullable `deletedAt` field.

---

### 2.1 `users`

```json
{
  "_id": "ObjectId()",
  "email": "<hashed>",
  "passwordHash": "<argon2>",
  "isActive": true,
  "subscriptionPlan": "free",
  "createdAt": "ISODate()",
  "updatedAt": "ISODate()",
  "deletedAt": null
}
```

**Embedding decision**: Never embed mutable sub-documents (e.g., messages) here; keep the user document minimal for fast authentication lookups.

---

### 2.2 `profiles`

```json
{
  "_id": "ObjectId()",
  "userId": "ObjectId()",
  "firstName": "Jane",
  "lastName": "Doe",
  "timeZone": "America/New_York",
  "preferredLanguage": "en-US",
  "birthDate": "ISODate()",
  "lifeDomains": ["mental_health", "productivity", "fitness"],
  "communicationStyle": "supportive",
  "wellnessScore": {
    "overall": 82,
    "sleep": 20,
    "mood": 20,
    "productivity": 15,
    "habits": 15,
    "fitness": 10,
    "learning": 10,
    "relationships": 10
  },
  "scoreHistory": [
    {
      "date": "ISODate()",
      "overall": 78,
      "sleepQuality": 5,
      "mood": 7,
      "energy": 6
    }
  ],
  "personalizationBlueprint": {
    "tone": "supportive",
    "depth": "intermediate",
    "domains": ["mental_health", "productivity"]
  },
  "createdAt": "ISODate()",
  "updatedAt": "ISODate()"
}
```

**Why embed**: Profile data and the current wellness score are always needed together with the user record; embedding avoids a join and stays well below the 16 MiB document limit.

---

### 2.3 `conversations`

```json
{
  "_id": "ObjectId()",
  "userId": "ObjectId()",
  "type": "coaching",
  "title": "Mindfulness Coaching",
  "sessionType": "assessment",
  "agentId": "mental_wellness",
  "startedAt": "ISODate()",
  "metadata": {
    "sessionTheme": "anxiety_management",
    "lastActivity": "ISODate()"
  },
  "messages": [
    {
      "_id": "ObjectId()",
      "sender": "user",
      "content": "I'm feeling overwhelmed at work",
      "position": 1,
      "status": "active",
      "createdAt": "ISODate()"
    },
    {
      "_id": "ObjectId()",
      "sender": "ai",
      "content": "Let's explore that together…",
      "position": 2,
      "status": "active",
      "createdAt": "ISODate()"
    }
  ],
  "createdAt": "ISODate()",
  "updatedAt": "ISODate()",
  "deletedAt": null
}
```

**Conversation type enum**: `coaching`, `goal_planning`, `habit_setup`, `journal`, `assessment`  
**Session type enum**: `assessment`, `nudge`, `reflection`, `escalation`

**Why embed**: Messages are always read in the context of their parent conversation, and the total size per conversation stays comfortably within the 16 MiB limit. Embedding provides atomic reads and simplifies Atlas-SQL analytics (the messages array maps to a child table).

---

### 2.4 `journal_entries`

```json
{
  "_id": "ObjectId()",
  "userId": "ObjectId()",
  "title": "Sunday Reflections",
  "body": "Practiced mindful breathing for 10 minutes, felt calmer.",
  "moodScore": 6,
  "entryDate": "ISODate()",
  "metadata": {
    "tags": ["mental_health", "work_life_balance"],
    "highlightedNotes": [
      {
        "text": "My breath was shallow during meetings",
        "timestamp": "ISODate()"
      }
    ]
  },
  "createdAt": "ISODate()",
  "deletedAt": null
}
```

**Why reference**: Journal entries are time-series data that grow indefinitely. Keeping them in a separate collection enables efficient range queries, TTL indexes, and avoids bloating the users document.

---

### 2.5 `goals`

```json
{
  "_id": "ObjectId()",
  "userId": "ObjectId()",
  "title": "Run a half-marathon",
  "description": "Complete a 21km race by December 2026",
  "pillar": "fitness",
  "targetDate": "ISODate()",
  "status": "active",
  "progress": 25,
  "milestones": [
    {
      "title": "Run 5km without stopping",
      "targetDate": "ISODate()",
      "completed": true
    }
  ],
  "relatedHabits": ["ObjectId()"],
  "tags": ["fitness", "endurance"],
  "createdAt": "ISODate()",
  "updatedAt": "ISODate()",
  "deletedAt": null
}
```

**Status enum**: `active`, `completed`, `canceled`, `paused`

---

### 2.6 `habits`

```json
{
  "_id": "ObjectId()",
  "userId": "ObjectId()",
  "name": "Morning meditation",
  "pillar": "mental_health",
  "frequency": "daily",
  "reminderTime": "07:00",
  "currentStreak": 12,
  "longestStreak": 30,
  "checkIns": [
    {
      "date": "ISODate()",
      "checkedAt": "ISODate()",
      "note": "Felt calm after 10 minutes"
    }
  ],
  "status": "active",
  "createdAt": "ISODate()",
  "updatedAt": "ISODate()",
  "deletedAt": null
}
```

**Frequency enum**: `daily`, `weekly`, `weekdays`, `weekends`, `custom`

---

### 2.7 `mood_entries`

```json
{
  "_id": "ObjectId()",
  "userId": "ObjectId()",
  "mood": "calm",
  "intensity": 7,
  "note": "Had a productive morning",
  "recordedAt": "ISODate()",
  "createdAt": "ISODate()"
}
```

**Mood enum**: `happy`, `calm`, `sad`, `anxious`, `angry`, `energized`, `tired`, `focused`, `overwhelmed`, `neutral`

---

### 2.8 `ai_insights`

```json
{
  "_id": "ObjectId()",
  "userId": "ObjectId()",
  "insightType": "wellness_trend",
  "pillar": "mental_health",
  "payload": {
    "trend": "decreasing_mood",
    "correlation": {
      "sleepQuality": 0.78,
      "journalTags": ["stress"]
    },
    "recommendation": "Consider a 5-minute breathing exercise before bed."
  },
  "generatedAt": "ISODate()",
  "expiresAt": "ISODate()",
  "createdAt": "ISODate()",
  "deletedAt": null
}
```

**Insight type enum**: `wellness_trend`, `risk_alert`, `goal_suggestion`, `habit_recommendation`, `burnout_warning`, `learning_insight`

**Why reference**: Insights are generated asynchronously and may be numerous per user. A dedicated collection allows indexing on `{userId, insightType}` and straightforward expiration via a TTL index.

---

### 2.9 `documents` (Knowledge Brain)

```json
{
  "_id": "ObjectId()",
  "userId": "ObjectId()",
  "title": "Deep Work",
  "type": "book",
  "sourceUrl": null,
  "mimeType": "application/pdf",
  "fileSizeBytes": 2048000,
  "version": 1,
  "ingestionStatus": "completed",
  "tags": ["productivity", "focus"],
  "pageCount": 296,
  "createdAt": "ISODate()",
  "updatedAt": "ISODate()",
  "deletedAt": null
}
```

**Document type enum**: `book`, `pdf`, `notes`, `research_paper`, `article`  
**Ingestion status enum**: `pending`, `processing`, `completed`, `failed`

---

### 2.10 `memory_links` (Mapping Qdrant Vectors to Users)

```json
{
  "_id": "ObjectId()",
  "userId": "ObjectId()",
  "vectorId": "qdrant-uuid-string",
  "source": "conversation:5e9d9a4d...",
  "sourceType": "journal",
  "createdAt": "ISODate()",
  "deletedAt": null
}
```

**Why reference**: The vector itself lives in Qdrant; we only keep a lightweight reference here for lookups and cleanup.

---

### 2.11 `wellness_challenges`

```json
{
  "_id": "ObjectId()",
  "userId": "ObjectId()",
  "challengeType": "7_day_focus_sprint",
  "title": "7-Day Focus Sprint",
  "description": "Complete 4 deep-work blocks daily for 7 days.",
  "startDate": "ISODate()",
  "endDate": "ISODate()",
  "status": "active",
  "progress": 3,
  "totalDays": 7,
  "createdAt": "ISODate()"
}
```

---

### 2.12 `subscriptions`

```json
{
  "_id": "ObjectId()",
  "userId": "ObjectId()",
  "plan": "free",
  "stripeCustomerId": "cus_...",
  "stripeSubscriptionId": "sub_...",
  "currentPeriodStart": "ISODate()",
  "currentPeriodEnd": "ISODate()",
  "cancelAtPeriodEnd": false,
  "status": "active",
  "createdAt": "ISODate()",
  "updatedAt": "ISODate()"
}
```

---

### 2.13 `audit_log` (PostgreSQL — Unchanged)

> The audit log remains in **PostgreSQL** because it requires strict ACID guarantees and immutable storage. No schema changes are required for the MongoDB migration.

```sql
CREATE TABLE audit_log (
  id            BIGSERIAL PRIMARY KEY,
  user_id       UUID NOT NULL,
  action        VARCHAR(100) NOT NULL,
  resource_type VARCHAR(50),
  resource_id   UUID,
  metadata      JSONB,
  ip_address    INET,
  performed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_log_user ON audit_log (user_id, performed_at DESC);
```

---

## 3. Embedding vs. Referencing — Decision Guide

| Data Domain | Recommended Pattern | Reason |
|-------------|--------------------|---------| 
| User + Profile + Current WellnessScore | **Embedding** (profile embedded in users) | One-to-one, read-heavy, stays under doc size limit |
| Conversation + Messages | **Embedding** (messages array inside conversations) | Messages always fetched with conversation; typical size < 16 MiB |
| Goals + Milestones | **Embedding** (milestones array inside goals) | Milestones are always read with their goal; bounded array |
| Habits + Check-ins | **Embedding** (checkIns array inside habits) | Check-ins always read in habit context; bounded by TTL cleanup |
| Journal entries | **Referencing** (`journal_entries` collection) | Unbounded growth, time-series queries, TTL support |
| AI insights | **Referencing** (`ai_insights` collection) | Potentially many per user; need independent TTL & indexing |
| Qdrant vector links | **Referencing** (`memory_links` collection) | Vector stored externally; only need lightweight pointer |
| Subscriptions / Billing | **MongoDB** (`subscriptions` collection) | User-centric, no multi-phase transaction requirements |

> **Guideline**: Embed when the sub-document is always accessed together with its parent and its total size is predictable (well under 16 MiB). Reference when the data is high-cardinality, grows without bound, or is updated independently.

---

## 4. Atlas SQL Compatibility Tips

1. **Flat field names** – avoid deeply nested or polymorphic arrays; every array element maps to a child table with a deterministic schema.
2. **Enum values** – store as short strings (`"coaching"`, `"goal_planning"`). Atlas SQL treats them as `VARCHAR`.
3. **Date fields** – always `ISODate`; Atlas SQL maps to `TIMESTAMP WITH TIME ZONE`.
4. **ObjectId handling** – use the `OBJECTID('hexstring')` function in Atlas SQL queries.
5. **Indexes for SQL** – create the following indexes to guarantee efficient analytical queries:

```javascript
// users
{ "email": 1, "isActive": 1 }

// profiles (indexed for reference lookups)
{ "userId": 1 }

// conversations
{ "userId": 1, "startedAt": -1 }

// journal_entries
{ "userId": 1, "entryDate": 1 }

// ai_insights
{ "userId": 1, "insightType": 1 }

// memory_links
{ "userId": 1, "vectorId": 1 }

// goals
{ "userId": 1, "status": 1 }

// habits
{ "userId": 1, "status": 1 }

// mood_entries
{ "userId": 1, "recordedAt": -1 }
```

6. **TTL indexes** – for GDPR-compliant purging:

```javascript
// journal_entries — 180 days after soft-delete
db.journal_entries.createIndex({ "deletedAt": 1 }, { expireAfterSeconds: 15552000 })

// ai_insights — optional TTL on expiresAt
db.ai_insights.createIndex({ "expiresAt": 1 }, { expireAfterSeconds: 0 })
```

7. **Sample Atlas-SQL queries** (for analytics dashboards):

```sql
-- Active users in the last 30 days
SELECT _id, email, isActive, updatedAt
FROM   Lumenly.users
WHERE  updatedAt >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY);

-- Average mood per month per user
SELECT userId,
       DATE_TRUNC('month', entryDate) AS month,
       AVG(moodScore) AS avgMood
FROM   Lumenly.journal_entries
GROUP BY userId, month
ORDER BY month DESC;

-- Count of AI insights generated per user last week
SELECT userId,
       COUNT(*) AS insightCount
FROM   Lumenly.ai_insights
WHERE  generatedAt >= DATE_SUB(CURRENT_DATE, INTERVAL 7 DAY)
GROUP BY userId;

-- Latest 5 messages of a conversation (via child table)
SELECT _id, sender, content, position, createdAt
FROM   Lumenly.conversations_messages
WHERE  conversationId = OBJECTID('66b5c3f1c1234567890abcd3')
ORDER BY position DESC
LIMIT 5;

-- Wellness score trend per user (last 30 days)
SELECT userId,
       DATE(date) AS scoreDate,
       overall
FROM   Lumenly.profiles_scoreHistory
WHERE  date >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY)
ORDER BY userId, scoreDate;
```

---

## 5. Sharding & Scaling

- **Shard key**: `hashed(userId)` – provides uniform distribution while keeping all of a single user's documents on the same shard (critical for embedded patterns).
- **Chunk size**: Default 64 MiB; monitor via Atlas UI and adjust if fragmentation appears.
- **Zone sharding** (optional): Map specific `userId` ranges to geographic zones (EU vs. US) to meet data-residency requirements.
- **Read replicas**: Dedicated read replicas for analytics queries via Atlas SQL Interface (avoids contention with write traffic).

---

## 6. Operational Checklist

| Item | Action |
|------|--------|
| **Backup** | Enable Atlas Continuous Cloud Backup with 30-day retention. |
| **Monitoring** | Set alerts on CPUUtilization, CacheUtilization, ShardImbalance, and IndexMissRatio. |
| **Security** | Enforce IP whitelisting, TLS 1.3, and least-privilege Atlas roles. |
| **Compliance** | Retain `deletedAt` TTL for GDPR-related collections; keep audit logs in PostgreSQL. |
| **Performance** | Use Atlas Performance Advisor to suggest missing indexes (e.g., on `metadata.tags`). |
| **Testing** | Validate all Atlas-SQL queries against a staging cluster before production rollout. |

---

## 7. Migration Roadmap (PostgreSQL → MongoDB Atlas)

1. Export schema (`pg_dump --schema-only --format=json`) → generate JSON skeletons.
2. Transform each table into the JSON structures shown above (e.g., `bigint` → `ObjectId`, `TIMESTAMPTZ` → `ISODate`, `JSONB` → native BSON).
3. Live Migration using Atlas Live Migration Service or `mongoimport` with batches.
4. Application refactor — replace ORM calls with async Beanie/Motor driver calls.
5. Verification — run identical analytics via Atlas-SQL on source vs. target and compare row counts & checksums.
6. Cut-over — switch read traffic after checksum ≥ 99.999% consistency; keep PostgreSQL read-only for a 48-hour grace period.

---

## 8. Future Extensibility

- **Multi-tenant support** – Add a `tenantId` field to every collection and include it in the shard key: `hashed({ tenantId, userId })`.
- **Role-Based Access Control** – Store `roles`, `rolePermissions`, `userRoles` as separate collections; enforce via MongoDB Realm Functions.
- **Hybrid analytics** – Combine Atlas-SQL for reporting with MongoDB Charts for visual dashboards of wellness trends and conversation volume.

---

## 9. Summary

- **MongoDB Atlas** now hosts all mutable user-facing data using clean, flat document schemas that map directly to the Atlas SQL interface.
- **Embedding** is applied to profiles, current wellnessScore, messages (inside conversations), milestones (inside goals), and check-ins (inside habits) where read patterns demand atomic retrieval and document size is bounded.
- **Referencing** is used for unbounded, time-series data (journal_entries, mood_entries), AI-generated insights, and Qdrant vector links.
- **Sharding** by `hashed(userId)` scales the design to the target 10M active users while keeping per-user data colocated.
- **Redis** and **Qdrant** remain untouched and continue to provide caching and vector search, respectively.

---

*Prepared by the Lumenly Engineering Team — 2026-06-23.*