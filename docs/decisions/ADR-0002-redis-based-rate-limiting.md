# ADR-0002: Redis-Based Distributed Rate Limiting with Fail-Closed Behavior

## Status

Accepted

## Context

Lumenly is a web application that needs to:
- Protect API endpoints from abuse and denial-of-service attacks
- Enforce per-user and per-IP rate limits across multiple workers
- Support endpoint-specific rate limits (login, registration, AI requests, etc.)
- Handle WebSocket message rate limiting
- Ensure security-critical endpoints remain protected even if rate limiting service fails

In-memory rate limiting (per-process) would not work across multiple workers and would reset on restart. Database-backed rate limiting would add latency to every request. A distributed cache like Redis provides low-latency, distributed rate limiting with persistence.

## Decision

Lumenly uses Redis-based distributed rate limiting with the following characteristics:

**Algorithm:**
- Sliding window algorithm using Redis sorted sets
- Configurable time windows (60s, 3600s, etc.)
- Per-user and per-IP isolation
- Endpoint-specific limits

**Implementation:**
- Global rate limiting middleware in `apps/backend/app/middleware/rate_limit.py`
- Endpoint-specific rate limiting in `apps/backend/app/middleware/endpoint_rate_limit.py`
- WebSocket rate limiting in coaching endpoints

**Fail-Closed Behavior:**
- Default behavior: RATE_LIMIT_FAIL_OPEN = False
- On Redis failure: Block all requests (return 503 Service Unavailable)
- Rationale: Security-critical endpoints must remain protected even if rate limiting service fails
- Configurable fail-open for development only

**Trusted Proxy Validation:**
- X-Forwarded-For header ignored unless trusted proxy configured
- CIDR range support for trusted proxies
- Prevents IP spoofing through proxy headers

**Endpoint-Specific Limits:**
- Login: 5 per 60s (per IP)
- Registration: 5 per 3600s (per IP)
- Refresh: 10 per 60s (per user)
- AI requests: 20 per 60s (per user)
- Document uploads: 10 per 60s (per user)
- General authenticated: 100 per 60s (per user)
- Admin requests: 1000 per 60s (per user)
- Public anonymous: 10 per 60s (per IP)
- WebSocket connections: 10 per hour (per user)
- WebSocket messages: 60 per minute (per user)
- WebSocket tool calls: 10 per minute (per user)

## Consequences

### Positive

- Distributed rate limiting works across multiple workers
- Low-latency checks (Redis is in-memory)
- Persistent state (survives worker restarts)
- Endpoint-specific limits provide appropriate protection per use case
- Fail-closed behavior ensures security is not compromised on Redis failure
- Trusted proxy validation prevents IP spoofing

### Negative

- Dependency on Redis for all API requests
- Fail-closed behavior may cause service disruption if Redis fails
- Increased operational complexity (Redis cluster for production)
- Need to monitor Redis health and performance

### Risks

- Redis failure causes service disruption (fail-closed)
- Redis misconfiguration may allow abuse
- Network latency to Redis may affect API performance
- Redis cluster complexity in production

## Evidence

**Implementation Evidence:**
- Rate limiting middleware in `apps/backend/app/middleware/rate_limit.py`
- Endpoint-specific rate limiting in `apps/backend/app/middleware/endpoint_rate_limit.py`
- Configuration in `apps/backend/app/core/config.py` (RATE_LIMIT_FAIL_OPEN, RATE_LIMIT_TRUSTED_PROXIES)
- WebSocket rate limiting in `apps/backend/app/api/endpoints/coaching.py`

**Test Evidence:**
- `test_rate_limiting.py` - General rate limiting tests
- `test_ai_document_rate_limiting.py` (6 tests) - Document upload rate limiting
- `test_auth_rate_limiting.py` (8 tests) - Authentication rate limiting
- `test_multi_worker_rate_limiting.py` (8 tests) - Distributed rate limiting
- `test_rate_limit_http_contract.py` (9 tests) - HTTP contract validation
- All tests passing in Phase 12.5

**Historical Context:**
- Implemented during Phase 12.5 security hardening
- Decision documented in Phase 12.5 reports
- Consistent with security requirements in documentation

## Alternatives Considered

**In-Memory Rate Limiting:**
- Pros: No external dependency, low latency
- Cons: Not distributed across workers, resets on restart, no persistence

**Database-Backed Rate Limiting:**
- Pros: Distributed, persistent
- Cons: Higher latency, adds load to database, not optimized for rate limiting

**API Gateway Rate Limiting:**
- Pros: Centralized, offloaded from application
- Cons: Additional infrastructure cost, less flexible for endpoint-specific limits

**Fail-Open Behavior:**
- Pros: Service continues operating on Redis failure
- Cons: Security compromised, endpoints vulnerable to abuse
- Rejected: Security-critical endpoints must remain protected

## References

- Rate limiting middleware: `apps/backend/app/middleware/rate_limit.py`
- Endpoint-specific rate limiting: `apps/backend/app/middleware/endpoint_rate_limit.py`
- Configuration: `apps/backend/app/core/config.py`
- WebSocket rate limiting: `apps/backend/app/api/endpoints/coaching.py`
- Phase 12.5 reports: `PHASE_12_5_FINAL_REPORT.md`, `PHASE_12_5_IMPLEMENTATION_REPAIR_REPORT.md`
