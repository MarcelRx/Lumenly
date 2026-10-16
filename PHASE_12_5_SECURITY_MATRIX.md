# Phase 12.5 — Rate Limiting & API Abuse Protection
# Security Matrix

## Audit Summary

### Current Rate Limiting Architecture
- **Implementation**: Redis-based sliding window algorithm (`app/middleware/rate_limit.py`)
- **Middleware**: Global HTTP middleware (`app/main.py` line 123)
- **Backend**: Redis with sorted sets (sliding window)
- **Configuration**: 
  - `RATE_LIMIT_ENABLED = True`
  - `RATE_LIMIT_FAIL_OPEN = False` (FAIL-CLOSED for security)
  - Anonymous: 10 req/min
  - Authenticated: 100 req/min
  - Admin: 1000 req/min
- **Identity**: Authenticated → `user_id` from JWT; Anonymous → IP from `X-Forwarded-For` or `request.client.host`
- **WebSocket**: Separate limits in `coaching.py` (10 conn/hour, 60 msg/min, 10 tool calls/min)

### Endpoints Inventory

| Endpoint | Method | Current Protection | Risk Level | Gap |
|----------|--------|-------------------|------------|-----|
| `/api/v1/auth/register` | POST | Global anonymous limit (10/min) | Medium | ✅ Adequate |
| `/api/v1/auth/login` | POST | Global anonymous limit (10/min) | High | ⚠️ Should be stricter |
| `/api/v1/auth/refresh` | POST | Global authenticated limit (100/min) | High | ⚠️ Should be stricter |
| `/api/v1/auth/logout` | POST | Global authenticated limit (100/min) | Low | ✅ Adequate |
| `/api/v1/auth/me` | GET | Global authenticated limit (100/min) | Low | ✅ Adequate |
| `/v1/ai/ask` | POST | Global authenticated limit (100/min) | High | ❌ Needs specific limit |
| `/v1/coaching/ws` | WebSocket | WS-specific limits | High | ✅ Adequate |
| `/api/v1/documents/` | POST | Global authenticated limit (100/min) | High | ❌ Needs specific limit |
| `/api/v1/documents/{id}` | GET | Global authenticated limit (100/min) | Low | ✅ Adequate |
| `/api/v1/journals/` | POST | Global authenticated limit (100/min) | Medium | ⚠️ Should monitor |
| `/api/v1/memory/` | POST | Global authenticated limit (100/min) | Medium | ⚠️ Should monitor |

### Security Policy Matrix

| Surface | Protection Required? | Limiting Identity | Limit | Window | Failure Behavior |
|---------|---------------------|-------------------|-------|--------|------------------|
| **Authentication (login)** | Yes | IP-based (anonymous) | 5 | 1 minute | Fail-closed |
| **Authentication (register)** | Yes | IP-based (anonymous) | 5 | 1 hour | Fail-closed |
| **Token Refresh** | Yes | User-based | 10 | 1 minute | Fail-closed |
| **AI/LLM (ask)** | Yes | User-based | 20 | 1 minute | Fail-closed |
| **Document Upload** | Yes | User-based | 10 | 1 minute | Fail-closed |
| **WebSocket Connections** | Yes | User-based | 10 | 1 hour | Fail-closed |
| **WebSocket Messages** | Yes | User-based | 60 | 1 minute | Fail-closed |
| **WebSocket Tool Calls** | Yes | User-based | 10 | 1 minute | Fail-closed |
| **Public Endpoints** | Yes | IP-based | 10 | 1 minute | Fail-closed |
| **Authenticated General** | Yes | User-based | 100 | 1 minute | Fail-closed |
| **Admin Endpoints** | Yes | User-based | 1000 | 1 minute | Fail-closed |

### Critical Gaps

1. **AI Endpoint Specific Limiting**: Currently shares 100 req/min with all authenticated endpoints. LLM calls are expensive and should be limited to ~20/min.
2. **Document Upload Specific Limiting**: Currently shares 100 req/min. Upload triggers expensive Celery tasks. Should be limited to ~10/min.
3. **Login Endpoint Stricter Limiting**: Currently 10/min for anonymous. Authentication attacks are common; should be 5/min.
4. **Refresh Endpoint Stricter Limiting**: Currently 100/min. Token refresh abuse should be limited to ~10/min.
5. **Proxy Header Trust Validation**: `X-Forwarded-For` is blindly accepted. No trusted proxy configuration exists.
6. **Concurrent Request Race Conditions**: Not tested. Redis pipeline usage should be verified under concurrency.
7. **Multi-Worker Shared State**: Not verified. Redis should ensure shared state across workers.

### Implementation Plan

1. Add endpoint-specific rate limiting decorators/dependencies
2. Implement stricter limits for sensitive endpoints
3. Add proxy header trust validation
4. Add concurrent request testing
5. Add multi-worker verification tests
6. Verify Redis failure/recovery behavior
7. Add comprehensive integration tests
