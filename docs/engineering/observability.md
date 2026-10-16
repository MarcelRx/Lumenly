# Observability and Error Handling

## Structured Logs

### Logging Configuration

**Location:** `apps/backend/app/core/logging_config.py`

**Implementation:**
- Structured logging with JSON format
- Request correlation via X-Request-ID header
- Context propagation via contextvars
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Environment-specific configuration (development, staging, production)

**Log Fields:**
- timestamp
- level
- logger name
- message
- event (for structured events)
- request_id (from context)
- method (for HTTP requests)
- path (for HTTP requests)
- status_code (for HTTP responses)
- duration_ms (for HTTP requests)
- error_type (for errors)
- error_message (for errors)
- Additional context-specific fields

**Evidence:**
- `apps/backend/app/core/logging_config.py`
- Request correlation middleware in `apps/backend/app/main.py`

### Request Correlation

**Implementation:**
- X-Request-ID header validation
- UUID v4 generation if header missing or invalid
- Context propagation via contextvars
- Request ID included in all logs
- Request ID returned in response headers

**Middleware:** `add_process_time_and_uuid_middleware` in `apps/backend/app/main.py`

**Evidence:**
- Request correlation middleware in `apps/backend/app/main.py`

## Metrics and Metric Names

### Prometheus Metrics

**Location:** `apps/backend/app/core/metrics.py`

**Metric Categories:**

**HTTP Metrics:**
- `http_requests_total`: Total HTTP requests (labels: method, path, status)
- `http_request_duration_seconds`: HTTP request duration (labels: method, path, status)
- `http_requests_in_progress`: In-flight HTTP requests

**Database Metrics:**
- `database_health_status`: Database health (labels: database, status)
- `database_query_duration_seconds`: Database query duration (labels: database, operation)

**Rate Limiting Metrics:**
- `rate_limit_violations_total`: Rate limit violations (labels: limit_type, user_role)
- `security_rate_limit_exceeded_total`: Security rate limit exceeded (labels: resource_type)

**WebSocket Metrics:**
- `websocket_connections_total`: Total WebSocket connections
- `websocket_active_connections`: Active WebSocket connections
- `websocket_disconnects_total`: WebSocket disconnects
- `websocket_messages_total`: WebSocket messages sent
- `websocket_message_failures_total`: WebSocket message failures

**Security Metrics:**
- `security_authorization_failures_total`: Authorization failures (labels: resource_type)
- `security_cross_tenant_attempts_total`: Cross-tenant access attempts (labels: resource_type)

**Evidence:**
- `apps/backend/app/core/metrics.py`
- Metrics endpoint at `/v1/metrics`

### Metrics Endpoint

**Location:** `/v1/metrics`

**Format:** Prometheus text format

**Access:**
- Requires authentication (in production)
- No rate limiting (metrics endpoint excluded)

**Evidence:**
- Metrics router in `apps/backend/app/api/endpoints/metrics.py`
- Rate limiting exclusions in `apps/backend/app/middleware/rate_limit.py`

## Distributed Tracing

### Current Status

**Implementation:** Not implemented

**Planned:**
- OpenTelemetry integration
- Distributed tracing across services
- Span propagation across HTTP and WebSocket
- Trace correlation with request IDs

**Evidence:**
- No tracing code found in repository

## Request Correlation

### Implementation

**X-Request-ID Header:**
- Validated on incoming requests
- Generated if missing or invalid
- Propagated via contextvars
- Included in all logs
- Returned in response headers

**Context Propagation:**
- Uses Python contextvars for async-safe propagation
- Accessible via `get_request_id()` and `set_request_id()`
- Compatible with async FastAPI

**Evidence:**
- Request correlation middleware in `apps/backend/app/main.py`
- Logging configuration in `apps/backend/app/core/logging_config.py`

## Health and Readiness Checks

### Health Endpoints

**Liveness Probe (`/health/live`):**
- Purpose: Confirm application process is alive
- Dependencies: None (no external dependencies)
- Response: `{"status": "alive", "service": "lumenly-api"}`
- Timeout: None

**Readiness Probe (`/health/ready`):**
- Purpose: Determine if application can receive traffic
- Dependencies: PostgreSQL, MongoDB, Redis, Qdrant
- Response: Detailed health status for each dependency
- Timeout: 5 seconds per dependency
- Behavior: Returns 503 if any dependency is unhealthy

**Legacy Health Check (`/health`):**
- Purpose: Backward compatibility
- Dependencies: None
- Response: `{"status": "ok", "service": "lumenly-api"}`
- Timeout: None

**Evidence:**
- Health check endpoints in `apps/backend/app/main.py`

### Health Check Implementation

**PostgreSQL Health Check:**
- Execute `SELECT 1` query
- Timeout: 5 seconds
- Sets database_health_status metric

**MongoDB Health Check:**
- Execute `ping` command
- Timeout: 5 seconds
- Sets database_health_status metric

**Redis Health Check:**
- Execute `ping` command
- Timeout: 5 seconds
- Sets database_health_status metric

**Qdrant Health Check:**
- Execute `get_collections` call
- Timeout: 5 seconds
- Sets database_health_status metric

**Evidence:**
- Readiness check implementation in `apps/backend/app/main.py`

## Error Categories and Response Contracts

### Error Categories

**Authentication Errors:**
- Invalid credentials
- Expired token
- Invalid token
- Inactive user

**Authorization Errors:**
- Insufficient permissions
- Role-based access denied

**Rate Limiting Errors:**
- Rate limit exceeded
- Redis unavailable (fail-closed)

**Validation Errors:**
- Invalid input
- Missing required fields
- Schema validation failure

**Database Errors:**
- Connection failed
- Query failed
- Timeout

**AI Provider Errors:**
- LLM provider unavailable
- Embedding provider unavailable
- API key invalid

**Security Errors:**
- Prompt injection detected
- Cross-tenant access attempt
- Tool authorization failed

**Evidence:**
- Error handling in `apps/backend/app/main.py`
- Security validation in `apps/backend/app/ai/security.py`
- Tool registry in `apps/backend/app/ai/tools/registry.py`

### Response Contracts

**Standard Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": "Additional details (development only)"
  },
  "meta": {
    "requestId": "uuid",
    "timestamp": 1234567890
  }
}
```

**Rate Limit Response:**
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later."
  },
  "meta": {
    "retryAfter": 30
  }
}
```

**Headers:**
- `Retry-After`: Seconds until retry allowed (on 429)
- `X-Request-ID`: Request correlation ID

**Evidence:**
- Error response format in `apps/backend/app/main.py`
- Rate limiting middleware in `apps/backend/app/middleware/`

## Retry Policies and Timeouts

### Database Timeouts

**PostgreSQL:**
- Connection timeout: 5 seconds (health check)
- Query timeout: Not configured (uses SQLAlchemy defaults)

**MongoDB:**
- Connection timeout: 5 seconds (health check)
- Query timeout: Not configured (uses Motor defaults)

**Redis:**
- Connection timeout: 5 seconds (health check)
- Command timeout: Not configured (uses Redis defaults)

**Qdrant:**
- Connection timeout: 5 seconds (health check)
- Query timeout: Not configured (uses Qdrant defaults)

**Evidence:**
- Health check timeouts in `apps/backend/app/main.py`

### Retry Policies

**Current Status:**
- No explicit retry policies implemented
- Database drivers may have built-in retries
- No custom retry logic for external services

**Evidence:**
- No retry logic found in repository

## Circuit Breakers and Fallback Mechanisms

### Current Status

**Circuit Breakers:**
- Not implemented

**Fallback Mechanisms:**
- AI Orchestrator: enable_fallback flag for safe responses
- LLM Provider: Mock provider for test environment
- Embedding Provider: Mock provider for test environment
- Rate Limiting: Fail-closed behavior (configurable)

**Fallback Response:**
```
"I apologize, but I encountered an error processing your request. Please try again."
```

**Evidence:**
- AI Orchestrator fallback in `apps/backend/app/ai/orchestration/router.py`
- Provider selection in `apps/backend/app/api/deps.py`
- Rate limiting configuration in `apps/backend/app/core/config.py`

## Queue and Background-Job Failure Handling

### Current Status

**Celery:**
- Configuration exists in `apps/backend/app/core/celery_app.py`
- Beat configuration exists in `apps/backend/app/core/beat_config.py`
- No active background jobs verified
- No failure handling implemented

**Planned:**
- Document embedding jobs
- Analytics computations
- Nudge generation
- Insight generation

**Evidence:**
- Celery configuration in `apps/backend/app/core/celery_app.py`
- No background job tasks found

## AI Provider Failures

### LLM Provider Failures

**Groq:**
- Provider-specific error handling
- No automatic fallback to Gemini
- Error propagated to caller
- Orchestrator may provide fallback response

**Gemini:**
- Provider-specific error handling
- No automatic fallback to Groq
- Error propagated to caller
- Orchestrator may provide fallback response

**Mock:**
- Always succeeds
- Used for test environment
- No API key required

**Evidence:**
- Provider implementations in `apps/backend/app/ai/llm/`
- Orchestrator fallback in `apps/backend/app/ai/orchestration/router.py`

### Embedding Provider Failures

**OpenAI/Cohere/FastEmbed/Sentence Transformers:**
- Provider-specific error handling
- No automatic fallback between providers
- Error propagated to caller
- Document ingestion fails on embedding failure

**Mock:**
- Always succeeds
- Returns fixed vector
- Used for test environment

**Evidence:**
- Provider implementations in `apps/backend/app/ai/embeddings/`

## Rate Limiting

### Implementation

**Redis-Based:**
- Sliding window algorithm using sorted sets
- Distributed across workers
- Per-user and per-IP isolation
- Configurable fail-closed/fail-open behavior

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

**Evidence:**
- Rate limiting middleware in `apps/backend/app/middleware/rate_limit.py`
- Endpoint-specific rate limiting in `apps/backend/app/middleware/endpoint_rate_limit.py`

### Rate Limiting Failure Behavior

**Redis Unavailable:**
- Fail-closed by default (RATE_LIMIT_FAIL_OPEN=False)
- Blocks requests on Redis failure
- Configurable fail-open for development only
- Logs Redis failures

**Trusted Proxy Validation:**
- X-Forwarded-For ignored unless trusted proxy configured
- CIDR range support for trusted proxies
- Client IP fallback when proxy not trusted

**Evidence:**
- Rate limiting configuration in `apps/backend/app/core/config.py`
- Trusted proxy validation in `apps/backend/app/middleware/endpoint_rate_limit.py`

## Redis and Other Infrastructure Outages

### Redis Outages

**Rate Limiting:**
- Fail-closed behavior (blocks requests)
- Configurable fail-open for development
- Metrics track Redis failures

**Short-Term Memory:**
- Errors logged and raised
- No fallback
- Conversation history lost

**Caching:**
- Errors logged and raised
- No fallback
- Cache misses handled gracefully

**Evidence:**
- Rate limiting middleware in `apps/backend/app/middleware/`
- Short-term memory in `apps/backend/app/ai/memory_engine/short_term.py`

### PostgreSQL Outages

**Authentication:**
- Health check fails
- Returns 503 on readiness check
- No automatic retry
- User cannot authenticate

**Audit Logs:**
- Compliance events cannot be written
- Errors logged
- No fallback

**Evidence:**
- Health check in `apps/backend/app/main.py`
- PostgreSQL dependency in authentication flow

### MongoDB Outages

**Domain Models:**
- Health check fails
- Returns 503 on readiness check
- No automatic retry
- CRUD operations fail

**Vector Metadata:**
- Memory links cannot be stored
- Document metadata cannot be stored
- Errors logged

**Evidence:**
- Health check in `apps/backend/app/main.py`
- MongoDB dependency in domain models

### Qdrant Outages

**Long-Term Memory:**
- Health check fails
- Returns 503 on readiness check
- No automatic retry
- Vector search fails

**Knowledge Retrieval:**
- Document chunks cannot be retrieved
- RAG falls back to memory-only
- Errors logged

**Evidence:**
- Health check in `apps/backend/app/main.py`
- Qdrant dependency in memory and knowledge brain

## Alerting and Dashboards

### Current Status

**Alerting:**
- Not implemented
- No alerting configuration found
- No monitoring dashboard configured

**Dashboards:**
- Not implemented
- No Grafana configuration found
- No dashboard definitions

**Metrics Available:**
- Prometheus metrics exported
- Can be scraped by Prometheus
- Can be visualized in Grafana (if configured)

**Evidence:**
- No alerting or dashboard configuration found
- Metrics endpoint available at `/v1/metrics`

## Recovery Procedures

### Service Recovery

**Procedure:**
1. Check health endpoints (`/health/live`, `/health/ready`)
2. Review service logs
3. Restart failed services
4. Verify service connectivity
5. Check configuration

**Evidence:**
- Health check endpoints in `apps/backend/app/main.py`
- Runbooks in `docs/runbooks/`

### Database Recovery

**PostgreSQL:**
- Runbook: `docs/runbooks/postgres-recovery.md`
- Runbook: `docs/runbooks/postgres-unavailable.md`

**MongoDB:**
- Runbook: `docs/runbooks/mongodb-recovery.md`
- Runbook: `docs/runbooks/mongodb-unavailable.md`

**Redis:**
- Runbook: `docs/runbooks/redis-recovery.md`
- Runbook: `docs/runbooks/redis-unavailable.md`

**Qdrant:**
- Runbook: `docs/runbooks/qdrant-recovery.md`
- Runbook: `docs/runbooks/qdrant-unavailable.md`

**Evidence:**
- Runbooks in `docs/runbooks/`

### Application Recovery

**Procedure:**
1. Check application logs
2. Verify configuration
3. Restart application
4. Verify health checks
5. Monitor metrics

**Evidence:**
- Runbook: `docs/runbooks/backend-down.md`
- Runbook: `docs/runbooks/full-environment-recovery.md`

## Known Limitations

1. **No Distributed Tracing:** OpenTelemetry not implemented
2. **No Circuit Breakers:** No circuit breaker pattern for external services
3. **No Automatic Retries:** No retry policies for external services
4. **No Alerting:** No alerting configuration
5. **No Dashboards:** No monitoring dashboards configured
6. **Limited Background Jobs:** Celery configured but no active jobs
7. **No Synthetic Monitoring:** No synthetic transaction monitoring
