# ADR-0001: Multi-Database Architecture for Lumenly

## Status

Accepted

## Context

Lumenly is an AI-native life operating system that requires:

- User authentication and authorization with strong ACID guarantees
- Storage of flexible, schema-evolving domain models (goals, habits, journals, coaching sessions)
- High-performance caching and rate limiting
- Vector storage for semantic search and retrieval
- Immutable audit logs for compliance

A single database technology cannot optimally serve all these use cases. PostgreSQL provides strong ACID guarantees but is less flexible for schema evolution. MongoDB offers flexible document storage but lacks strong transactional guarantees for certain compliance scenarios. Redis provides high-performance caching but is not persistent. Qdrant specializes in vector search but is not a general-purpose database.

## Decision

Lumenly uses a multi-database architecture with each technology serving specific purposes:

**PostgreSQL:**

- User authentication and authorization (users table)
- Immutable audit logs (compliance events)
- Rationale: Strong ACID guarantees for authentication and compliance

**MongoDB Atlas:**

- Domain models (journal entries, goals, habits, coaching sessions, documents, AI insights)
- Flexible schema evolution
- Document-oriented data structures
- Rationale: Flexibility for evolving data models, horizontal scalability

**Redis:**

- Short-term memory (conversation history)
- Rate limiting counters (sliding window algorithm)
- Caching layer (profiles, session data)
- Rationale: High-performance caching and distributed rate limiting

**Qdrant:**

- Long-term memory vectors (semantic search)
- Knowledge base vectors (document chunks)
- Rationale: Specialized vector storage with high-performance ANN search

## Consequences

### Positive

- Each database technology is used for its strengths
- PostgreSQL provides strong ACID guarantees for authentication and compliance
- MongoDB provides flexibility for domain models and horizontal scalability
- Redis provides high-performance caching and distributed rate limiting
- Qdrant provides optimized vector search
- Clear separation of concerns between data types

### Negative

- Increased operational complexity (managing 4 different databases)
- Higher cost (4 separate database services)
- More connection management code
- Potential for data inconsistency across databases
- More complex backup and recovery procedures

### Risks

- Operational complexity may lead to misconfiguration
- Cross-database transactions are not possible
- Backup/recovery requires coordination across 4 systems
- Monitoring complexity increases

## Evidence

**Implementation Evidence:**

- PostgreSQL models in `apps/backend/app/models/user.py`
- MongoDB models in `apps/backend/app/models/domain.py`
- Redis usage in `apps/backend/app/db/redis.py` and rate limiting middleware
- Qdrant usage in `apps/backend/app/db/qdrant.py` and memory/knowledge brain
- Database connection code in `apps/backend/app/db/`

**Test Evidence:**

- Database fixtures in `apps/backend/tests/conftest.py` configure all 4 databases
- 832 tests passing with all 4 databases in Phase 12.5

**Historical Context:**

- Decision made during initial architecture design (Phase 0-1)
- No alternative single-database approaches were implemented
- Documented in legacy `docs/system_architecture.md` (now removed, content migrated to `docs/architecture/system-architecture.md`)

## Alternatives Considered

**Single PostgreSQL Database:**

- Pros: Simpler operations, ACID guarantees across all data
- Cons: Less flexible for schema evolution, no native vector search, poorer performance for caching

**Single MongoDB Database:**

- Pros: Flexible schema, horizontal scalability
- Cons: Weaker ACID guarantees for compliance, no specialized vector search, poor caching performance

**Single PostgreSQL + pgvector:**

- Pros: Single database, ACID guarantees, vector search
- Cons: Vector search performance lower than Qdrant, less flexible schema, poor caching performance

## References

- PostgreSQL connection: `apps/backend/app/db/postgres.py`
- MongoDB connection: `apps/backend/app/db/mongo.py`
- Redis connection: `apps/backend/app/db/redis.py`
- Qdrant connection: `apps/backend/app/db/qdrant.py`
- System architecture: `docs/architecture/system-architecture.md`
- Database design: `docs/database_design.md`
