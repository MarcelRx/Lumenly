# PHASE 10.1 — OBSERVABILITY CONTRACT

**Based on Forensic Audit:** PHASE10_1_OBSERVABILITY_FORENSIC_AUDIT.md  
**Date:** 2026-08-27  
**Status:** DRAFT

---

## OBSERVABILITY CONTRACT DEFINITION

This contract defines the minimal observability requirements for PHASE 10.1 implementation, based on the forensic audit findings. The objective is to enhance existing infrastructure without architectural changes.

---

## 1. REQUEST CORRELATION CONTRACT

### 1.1 HTTP Request Correlation

**Every HTTP request MUST provide:**
- `request_id`: Unique identifier (UUID v4 format)
- `method`: HTTP method (GET, POST, PUT, DELETE, etc.)
- `path`: Request path/route
- `status_code`: HTTP response status code
- `duration_ms`: Request processing time in milliseconds
- `timestamp`: Request start timestamp (ISO 8601)
- `service`: Service identifier ("lumenly-api")

**Implementation Requirements:**
- Accept `X-Request-ID` header if present and valid (UUID format, max 36 chars)
- Generate UUID v4 if header missing or invalid
- Store in `request.state.request_id` for async-safe access
- Return `X-Request-ID` in response header
- Add validation: reject malformed/oversized request IDs (>100 chars)
- Use `contextvars` for async-safe correlation across concurrent requests

**Exclusions:**
- Health probes (`/health/live`, `/health/ready`, `/health`) may use simplified logging
- Metrics endpoint (`/metrics`) may use simplified logging

### 1.2 Request ID Validation

**Valid Request ID Format:**
- UUID v4 format: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`
- Maximum length: 100 characters
- Must be string type

**Invalid Request ID Handling:**
- Reject silently and generate new UUID
- Log warning when rejecting invalid request ID
- Do not fail request due to invalid request ID

---

## 2. STRUCTURED LOGGING CONTRACT

### 2.1 Log Format

**Production Environment:**
- Format: JSON
- Encoding: UTF-8
- Timestamp: ISO 8601 with timezone
- Fields: Flat structure (no nested objects except where necessary)

**Development/Staging Environment:**
- Format: Plain text (human-readable)
- Color-coded output (optional)
- Include file/line numbers for debugging

### 2.2 Standard Log Fields

**Every log entry MUST include:**
```json
{
  "timestamp": "2026-08-27T10:30:45.123Z",
  "level": "INFO",
  "logger": "app.api.endpoints.ai",
  "message": "AI query processed",
  "service": "lumenly-api",
  "environment": "production",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Conditional Fields (when applicable):**
```json
{
  "user_id": "user-uuid",
  "method": "POST",
  "path": "/v1/ai/ask",
  "status_code": 200,
  "duration_ms": 123,
  "error_category": "validation_error",
  "task_id": "celery-task-id",
  "task_name": "process_document_task"
}
```

### 2.3 Log Level Usage

**DEBUG:**
- Detailed developer diagnostics
- Database query details (disabled in production)
- Detailed processing steps

**INFO:**
- Normal lifecycle events
- Request start/completion
- Task start/completion
- Connection lifecycle
- Configuration loading

**WARNING:**
- Recoverable anomalies
- Rate limit violations
- Retry attempts
- Suspicious behavior
- Security events (non-critical)

**ERROR:**
- Unexpected failures requiring investigation
- Database connection failures
- External service failures
- Task failures
- Authentication failures

**CRITICAL:**
- Startup failures
- Fatal errors
- Security breaches
- Data corruption

---

## 3. HTTP REQUEST OBSERVABILITY CONTRACT

### 3.1 Request Start Logging

**Every HTTP request (except health probes) MUST log:**
```json
{
  "event": "http_request_start",
  "request_id": "uuid",
  "method": "POST",
  "path": "/v1/ai/ask",
  "user_agent": "Mozilla/5.0...",
  "client_ip": "192.168.1.1"
}
```

### 3.2 Request End Logging

**Every HTTP request (except health probes) MUST log:**
```json
{
  "event": "http_request_end",
  "request_id": "uuid",
  "method": "POST",
  "path": "/v1/ai/ask",
  "status_code": 200,
  "duration_ms": 123,
  "user_id": "user-uuid"  // if authenticated
}
```

### 3.3 Error Request Logging

**Failed HTTP requests MUST log:**
```json
{
  "event": "http_request_error",
  "request_id": "uuid",
  "method": "POST",
  "path": "/v1/ai/ask",
  "status_code": 500,
  "duration_ms": 456,
  "error_category": "internal_error",
  "error_message": "Safe error message for client"
}
```

### 3.4 Health Probe Logging

**Health probes SHOULD use minimal logging:**
```json
{
  "event": "health_check",
  "probe": "liveness",
  "status": "healthy"
}
```

**Health checks SHOULD NOT log per-request in production**

---

## 4. EXCEPTION OBSERVABILITY CONTRACT

### 4.1 Server-Side Exception Logging

**Unexpected exceptions MUST log server-side:**
```json
{
  "event": "exception",
  "request_id": "uuid",
  "error_category": "unexpected_error",
  "error_type": "ValueError",
  "error_message": "Error message",
  "stack_trace": "Full stack trace (server only)",
  "method": "POST",
  "path": "/v1/ai/ask",
  "user_id": "user-uuid"
}
```

### 4.2 Client Error Responses

**Clients MUST NOT receive:**
- Stack traces
- Internal filesystem paths
- Database credentials
- Detailed internal error messages
- Implementation details

**Clients MUST receive:**
```json
{
  "success": false,
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "An unexpected error occurred on the server."
  },
  "meta": {
    "requestId": "uuid",
    "timestamp": 1724755845
  }
}
```

### 4.3 Expected Validation Errors

**Validation errors SHOULD use WARNING level:**
```json
{
  "event": "validation_error",
  "request_id": "uuid",
  "error_category": "validation_error",
  "field": "email",
  "validation_rule": "required"
}
```

---

## 5. CELERY OBSERVABILITY CONTRACT

### 5.1 Task Start Logging

**Every Celery task MUST log:**
```json
{
  "event": "task_start",
  "task_id": "uuid",
  "task_name": "process_document_task",
  "attempt": 1,
  "max_attempts": 4,
  "user_id": "user-uuid",
  "document_id": "document-id"
}
```

### 5.2 Task Success Logging

**Successful tasks MUST log:**
```json
{
  "event": "task_success",
  "task_id": "uuid",
  "task_name": "process_document_task",
  "duration_ms": 5000,
  "attempt": 1,
  "user_id": "user-uuid",
  "document_id": "document-id",
  "chunks_processed": 10
}
```

### 5.3 Task Failure Logging

**Failed tasks MUST log:**
```json
{
  "event": "task_failure",
  "task_id": "uuid",
  "task_name": "process_document_task",
  "duration_ms": 3000,
  "attempt": 2,
  "max_attempts": 4,
  "error_category": "transient_database_error",
  "error_type": "ConnectionFailure",
  "error_message": "Database connection failed",
  "will_retry": true,
  "user_id": "user-uuid",
  "document_id": "document-id"
}
```

### 5.4 Task Retry Logging

**Retry attempts MUST log:**
```json
{
  "event": "task_retry",
  "task_id": "uuid",
  "task_name": "process_document_task",
  "attempt": 2,
  "max_attempts": 4,
  "retry_backoff_seconds": 60,
  "error_category": "transient_database_error"
}
```

### 5.5 Celery Architecture Preservation

**MUST MAINTAIN:**
- Synchronous worker architecture
- No asyncio in Celery tasks
- Sync database clients
- Existing error classification
- Existing retry logic

**MUST NOT ADD:**
- asyncio.run()
- New event loops
- ThreadPoolExecutor
- Async database clients in workers

---

## 6. WEBSOCKET OBSERVABILITY CONTRACT

### 6.1 Connection Lifecycle Logging

**WebSocket connection accepted:**
```json
{
  "event": "websocket_connection_accepted",
  "session_id": "uuid",
  "user_id": "user-uuid",
  "client_ip": "192.168.1.1"
}
```

**WebSocket connection rejected (authentication):**
```json
{
  "event": "websocket_connection_rejected",
  "session_id": "uuid",
  "reason": "authentication_failed",
  "client_ip": "192.168.1.1"
}
```

**WebSocket connection rejected (rate limit):**
```json
{
  "event": "websocket_connection_rejected",
  "session_id": "uuid",
  "reason": "rate_limit_exceeded",
  "client_ip": "192.168.1.1",
  "user_id": "user-uuid"
}
```

### 6.2 Session Lifecycle Logging

**Session started:**
```json
{
  "event": "websocket_session_started",
  "session_id": "uuid",
  "user_id": "user-uuid",
  "session_type": "assessment"
}
```

**Session ended normally:**
```json
{
  "event": "websocket_session_ended",
  "session_id": "uuid",
  "user_id": "user-uuid",
  "duration_seconds": 1800,
  "reason": "client_disconnect"
}
```

**Session ended unexpectedly:**
```json
{
  "event": "websocket_session_ended",
  "session_id": "uuid",
  "user_id": "user-uuid",
  "duration_seconds": 900,
  "reason": "server_error"
}
```

### 6.3 Rate Limit Logging

**WebSocket rate limit events:**
```json
{
  "event": "websocket_rate_limit_exceeded",
  "user_id": "user-uuid",
  "limit_type": "message",
  "session_id": "uuid"
}
```

### 6.4 Message Content Policy

**MUST NOT LOG:**
- WebSocket message content
- User prompts
- AI responses
- Journal content
- Document content
- JWT tokens
- Authentication credentials

**MAY LOG:**
- Message count
- Message size (length)
- Message type (if applicable)

---

## 7. DATABASE/DEPENDENCY OBSERVABILITY CONTRACT

### 7.1 Connection Lifecycle

**Database connection events:**
```json
{
  "event": "database_connection_established",
  "database": "postgres",
  "host": "postgres-host"
}
```

```json
{
  "event": "database_connection_failed",
  "database": "postgres",
  "host": "postgres-host",
  "error_category": "connection_error"
}
```

### 7.2 Query Logging (Development Only)

**Development environment MAY log:**
```json
{
  "event": "database_query",
  "database": "postgres",
  "query": "SELECT * FROM users",
  "duration_ms": 5
}
```

**Production MUST NOT log:**
- Full database queries
- Query parameters
- User data in queries

### 7.3 Health Check Observability

**Dependency health status:**
```json
{
  "event": "dependency_health_check",
  "dependency": "postgres",
  "status": "healthy",
  "duration_ms": 5
}
```

### 7.4 Connection URL Policy

**MUST NOT LOG:**
- Database URLs with credentials
- Passwords in connection strings
- API keys in connection strings

**MAY LOG:**
- Host names
- Port numbers
- Database names
- Connection status

---

## 8. SECURITY OBSERVABILITY CONTRACT

### 8.1 Security Event Logging

**Preserve existing ComplianceEvent infrastructure:**
```python
ComplianceEvent(
    user_id=user_id,
    event_type="cross_tenant_access_attempt",
    severity_level=0.7,
    details={
        "resource_id": resource_id,
        "requesting_user": user_id,
        "resource_owner": document_user_id
    }
)
```

### 8.2 Authentication Events

**Authentication failure:**
```json
{
  "event": "authentication_failed",
  "user_id": "user-uuid",
  "reason": "invalid_password",
  "client_ip": "192.168.1.1"
}
```

**Rate limit violation:**
```json
{
  "event": "rate_limit_exceeded",
  "identifier": "user-uuid",
  "user_role": "authenticated",
  "path": "/v1/ai/ask",
  "method": "POST"
}
```

### 8.3 Cross-Tenant Access Attempts

**Cross-tenant access attempt:**
```json
{
  "event": "cross_tenant_access_attempt",
  "requesting_user": "user-a-uuid",
  "resource_owner": "user-b-uuid",
  "resource_type": "document",
  "resource_id": "document-id",
  "severity": "high"
}
```

### 8.4 Security Event Policy

**MUST LOG:**
- Authentication failures
- Authorization failures
- Cross-tenant access attempts
- Rate limit violations
- Invalid tool execution
- Suspicious tool arguments

**MUST NOT LOG:**
- Passwords
- JWT tokens
- API keys
- Session tokens
- Authorization headers

---

## 9. SECRET LEAKAGE PREVENTION CONTRACT

### 9.1 Prohibited Log Content

**MUST NEVER LOG:**
- Passwords (plain or hashed)
- JWT tokens (access or refresh)
- API keys (any provider)
- Authorization headers
- Cookie values with authentication material
- Database URLs with credentials
- Redis URLs with credentials
- MongoDB URLs with credentials
- Qdrant API keys
- LLM provider API keys

### 9.2 Sensitive User Data

**MUST NEVER LOG:**
- Journal entry content
- Document content
- User prompts
- AI responses containing user data
- Personal identifiable information (PII)
- Health information
- Financial information

### 9.3 Log Sanitization

**Implement sanitization layer for:**
- Authorization headers
- Cookie headers
- Any header containing "token", "key", "secret", "password"
- Request bodies (if logged)
- Response bodies (if logged)

**Sanitization pattern:**
```python
[REDACTED]
```

---

## 10. METRICS DECISION CONTRACT

### 10.1 Current State

**Existing Infrastructure:**
- Prometheus endpoint exists (`/metrics`)
- Prometheus client library installed
- Grafana dashboard defined
- Alerting rules defined

**Current Utilization:**
- Unclear if metrics are being collected
- Unclear if dashboards are being used
- Unclear if alerting is active

### 10.2 PHASE 10.1 Scope

**DO NOT IMPLEMENT in PHASE 10.1:**
- New metrics infrastructure
- OpenTelemetry integration
- Custom metrics collectors
- Metrics backend setup

**DOCUMENT for future phases:**
- Required metrics for PHASE 10.2
- Prometheus integration requirements
- Alerting rule requirements
- Dashboard requirements

### 10.3 Future Metrics Requirements

**HTTP Metrics (Future):**
- Request count by route, method, status
- Request latency percentiles (p50, p95, p99)
- Error rate by route, method
- Active request count

**Celery Metrics (Future):**
- Task count by task name, status
- Task duration percentiles
- Task retry rate
- Task failure rate
- Active worker count

**Database Metrics (Future):**
- Connection pool utilization
- Query latency percentiles
- Error rate by database
- Active connection count

**Security Metrics (Future):**
- Authentication failure rate
- Rate limit violation rate
- Cross-tenant access attempt rate
- Tool execution failure rate

---

## 11. IMPLEMENTATION PRIORITY

### Priority 1 (Critical - PHASE 10.1):
1. Request ID validation and propagation
2. Structured logging (JSON format for production)
3. HTTP request lifecycle logging
4. Exception observability enhancement
5. Secret leakage prevention

### Priority 2 (Important - PHASE 10.1):
6. Celery observability enhancement (structured)
7. WebSocket lifecycle logging enhancement
8. Security observability verification

### Priority 3 (Future - PHASE 10.2):
9. Metrics infrastructure
10. Advanced correlation/tracing
11. Performance monitoring
12. Alerting integration

---

## 12. TESTING REQUIREMENTS

### 12.1 Unit Tests
- Request ID generation and validation
- Structured logging format
- Log field completeness
- Secret sanitization
- Error categorization

### 12.2 Integration Tests
- End-to-end request correlation
- HTTP request logging
- Exception handling with correlation
- Celery task logging
- WebSocket lifecycle logging

### 12.3 Regression Tests
- Secret leakage prevention
- Existing security tests
- Tenant isolation tests
- Rate limiting tests
- Architecture preservation tests

### 12.4 Performance Tests
- Logging overhead impact
- Concurrent request correlation
- Async contextvar performance

---

## 13. NON-REQUIREMENTS

### What PHASE 10.1 Will NOT Do:
- Introduce OpenTelemetry
- Add distributed tracing beyond request IDs
- Implement metrics collection
- Change Celery architecture
- Modify security event logging (ComplianceEvent)
- Change health check endpoints
- Modify rate limiting implementation
- Introduce new dependencies unless necessary

### What PHASE 10.1 Will Preserve:
- Existing synchronous Celery architecture
- Existing ComplianceEvent infrastructure
- Existing security model
- Existing health check implementation
- Existing rate limiting implementation
- Existing WebSocket security model
- All existing test suites (497 passing baseline)

---

## 14. ACCEPTANCE CRITERIA

### 14.1 Functional Requirements
- [ ] Request IDs are validated and propagated
- [ ] Structured JSON logging in production
- [ ] HTTP request lifecycle observable
- [ ] Exceptions correlated with request IDs
- [ ] Celery tasks observable with structured data
- [ ] WebSocket lifecycle observable
- [ ] Security events remain observable
- [ ] No secrets appear in logs
- [ ] No user content appears in generic logs

### 14.2 Non-Functional Requirements
- [ ] Logging overhead < 5% of request time
- [ ] Concurrent requests have isolated correlation
- [ ] Existing tests remain passing (497 baseline)
- [ ] No architectural changes to Celery
- [ ] No changes to security model
- [ ] Graceful shutdown still works
- [ ] Docker deployment still works

### 14.3 Security Requirements
- [ ] No JWT/APi key/password logging
- [ ] No user content logging
- [ ] Authorization headers filtered
- [ ] Stack traces only in development
- [ ] Tenant isolation preserved
- [ ] Rate limiting preserved

---

**Contract Status:** READY FOR IMPLEMENTATION  
**Next Step:** Implement Priority 1 changes