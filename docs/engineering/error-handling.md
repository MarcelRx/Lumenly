# Error Handling

## Error Categories

### Authentication Errors

**Invalid Credentials:**
- HTTP Status: 401 Unauthorized
- Error Code: INVALID_CREDENTIALS
- Message: "Could not validate credentials"
- Evidence: `apps/backend/app/api/deps.py`

**Expired Token:**
- HTTP Status: 401 Unauthorized
- Error Code: TOKEN_EXPIRED
- Message: "Token has expired"
- Evidence: `apps/backend/app/api/deps.py`

**Invalid Token:**
- HTTP Status: 401 Unauthorized
- Error Code: INVALID_TOKEN
- Message: "Invalid or malformed token"
- Evidence: `apps/backend/app/api/deps.py`

**Inactive User:**
- HTTP Status: 401 Unauthorized
- Error Code: INACTIVE_USER
- Message: "Inactive user"
- Evidence: `apps/backend/app/api/deps.py`

### Authorization Errors

**Insufficient Permissions:**
- HTTP Status: 403 Forbidden
- Error Code: INSUFFICIENT_PERMISSIONS
- Message: "Insufficient permissions"
- Evidence: `apps/backend/app/api/deps.py`

### Rate Limiting Errors

**Rate Limit Exceeded:**
- HTTP Status: 429 Too Many Requests
- Error Code: RATE_LIMIT_EXCEEDED
- Message: "Too many requests. Please try again later."
- Headers: Retry-After (seconds)
- Evidence: `apps/backend/app/middleware/rate_limit.py`

**Redis Unavailable (Fail-Closed):**
- HTTP Status: 503 Service Unavailable
- Error Code: RATE_LIMIT_UNAVAILABLE
- Message: "Rate limiting service unavailable"
- Evidence: `apps/backend/app/middleware/rate_limit.py`

### Validation Errors

**Invalid Input:**
- HTTP Status: 422 Unprocessable Entity
- Error Code: VALIDATION_ERROR
- Message: Validation error details
- Evidence: Pydantic validation in FastAPI

**Missing Required Fields:**
- HTTP Status: 422 Unprocessable Entity
- Error Code: MISSING_FIELDS
- Message: "Missing required field: {field_name}"
- Evidence: Tool registry validation

### Database Errors

**Connection Failed:**
- HTTP Status: 503 Service Unavailable
- Error Code: DATABASE_CONNECTION_FAILED
- Message: "Database connection failed"
- Evidence: Health check implementation

**Query Failed:**
- HTTP Status: 500 Internal Server Error
- Error Code: DATABASE_QUERY_FAILED
- Message: "Database query failed"
- Evidence: Database error handling

**Timeout:**
- HTTP Status: 504 Gateway Timeout
- Error Code: DATABASE_TIMEOUT
- Message: "Database timeout"
- Evidence: Health check timeouts

### AI Provider Errors

**LLM Provider Unavailable:**
- HTTP Status: 503 Service Unavailable
- Error Code: LLM_PROVIDER_UNAVAILABLE
- Message: "LLM provider unavailable"
- Evidence: LLM provider error handling

**Embedding Provider Unavailable:**
- HTTP Status: 503 Service Unavailable
- Error Code: EMBEDDING_PROVIDER_UNAVAILABLE
- Message: "Embedding provider unavailable"
- Evidence: Embedding provider error handling

**Invalid API Key:**
- HTTP Status: 500 Internal Server Error
- Error Code: INVALID_API_KEY
- Message: "Invalid API key"
- Evidence: Provider validation

### Security Errors

**Prompt Injection Detected:**
- HTTP Status: 400 Bad Request
- Error Code: PROMPT_INJECTION_DETECTED
- Message: "Prompt injection detected"
- Evidence: AI security validation

**Cross-Tenant Access Attempt:**
- HTTP Status: 403 Forbidden
- Error Code: CROSS_TENANT_ACCESS_DENIED
- Message: "Access denied"
- Evidence: Tool registry security

**Tool Authorization Failed:**
- HTTP Status: 403 Forbidden
- Error Code: TOOL_AUTHORIZATION_FAILED
- Message: "User not authorized to execute tool"
- Evidence: Tool registry authorization

## Response Contracts

### Standard Error Response

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

**Fields:**
- success: Always false for errors
- error.code: Machine-readable error code
- error.message: Human-readable error message
- error.details: Additional details (development only, null in production)
- meta.requestId: Request correlation ID
- meta.timestamp: Unix timestamp

**Evidence:**
- Global exception handler in `apps/backend/app/main.py`

### Rate Limit Response

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
- Retry-After: Seconds until retry allowed
- X-Request-ID: Request correlation ID

**Evidence:**
- Rate limiting middleware in `apps/backend/app/middleware/`

## Retry Policies

### Current Status

**No Explicit Retry Policies:**
- No custom retry logic implemented
- Database drivers may have built-in retries
- No retry for external API calls
- No retry for AI provider calls

**Evidence:**
- No retry logic found in repository

### Planned Improvements

**Exponential Backoff:**
- For database connections
- For external API calls
- For AI provider calls

**Circuit Breakers:**
- For external services
- For AI providers
- For database connections

## Timeouts

### Database Timeouts

**PostgreSQL:**
- Health check timeout: 5 seconds
- Query timeout: Not configured (SQLAlchemy defaults)

**MongoDB:**
- Health check timeout: 5 seconds
- Query timeout: Not configured (Motor defaults)

**Redis:**
- Health check timeout: 5 seconds
- Command timeout: Not configured (Redis defaults)

**Qdrant:**
- Health check timeout: 5 seconds
- Query timeout: Not configured (Qdrant defaults)

**Evidence:**
- Health check timeouts in `apps/backend/app/main.py`

### AI Provider Timeouts

**LLM Providers:**
- No explicit timeout configured
- Uses provider defaults

**Embedding Providers:**
- No explicit timeout configured
- Uses provider defaults

**Evidence:**
- No timeout configuration found in provider implementations

## Circuit Breakers

### Current Status

**Not Implemented:**
- No circuit breaker pattern
- No fallback mechanisms for external services
- No service degradation

**Fallback Mechanisms:**
- AI Orchestrator: enable_fallback flag for safe responses
- Mock providers for test environment
- Rate limiting: Fail-closed behavior

**Evidence:**
- No circuit breaker code found
- AI Orchestrator fallback in `apps/backend/app/ai/orchestration/router.py`

## Fallback Mechanisms

### AI Orchestrator Fallback

**When Enabled:**
- Returns safe fallback response on error
- Response: "I apologize, but I encountered an error processing your request. Please try again."
- Agent type: "fallback"
- Confidence: 0.0

**When Disabled:**
- Raises exception to caller
- Caller must handle error

**Configuration:**
- enable_fallback parameter in AIOrchestrator constructor

**Evidence:**
- AI Orchestrator in `apps/backend/app/ai/orchestration/router.py`

### Provider Fallback

**Test Environment:**
- Always uses mock provider
- No API calls to external services

**Development/Staging:**
- Defaults to mock if no valid API keys
- Uses real provider if valid API key present

**Production:**
- Requires valid API key
- Fails if no valid API key

**Evidence:**
- Provider selection in `apps/backend/app/api/deps.py`

### Rate Limiting Fallback

**Fail-Closed (Default):**
- Blocks requests when Redis unavailable
- Returns 503 Service Unavailable
- Configurable via RATE_LIMIT_FAIL_OPEN

**Fail-Open (Development Only):**
- Allows requests when Redis unavailable
- Logs Redis failures
- Not recommended for production

**Evidence:**
- Rate limiting configuration in `apps/backend/app/core/config.py`

## Queue and Background-Job Failure Handling

### Current Status

**Celery Configuration:**
- Configuration exists in `apps/backend/app/core/celery_app.py`
- Beat configuration exists in `apps/backend/app/core/beat_config.py`
- No active background jobs verified
- No failure handling implemented

**Planned Background Jobs:**
- Document embedding jobs
- Analytics computations
- Nudge generation
- Insight generation

**Failure Handling:**
- Not implemented
- No retry policy configured
- No dead letter queue

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

## Rate Limiting Error Handling

### Redis Unavailable

**Fail-Closed Behavior:**
- Blocks all requests
- Returns 503 Service Unavailable
- Logs Redis failure
- Metrics track Redis failures

**Fail-Open Behavior:**
- Allows all requests
- Logs Redis failure
- No rate limiting enforced
- Only for development

**Evidence:**
- Rate limiting middleware in `apps/backend/app/middleware/rate_limit.py`
- Configuration in `apps/backend/app/core/config.py`

### Rate Limit Exceeded

**Response:**
- HTTP Status: 429 Too Many Requests
- Error body with error code and message
- Retry-After header with seconds until retry allowed
- Rate limit violation metric incremented

**Evidence:**
- Rate limiting middleware in `apps/backend/app/middleware/rate_limit.py`

## Redis Outages

### Rate Limiting

**Fail-Closed:**
- Blocks requests
- Returns 503
- Logs failure

**Fail-Open:**
- Allows requests
- Logs failure
- No rate limiting

### Short-Term Memory

**Error Handling:**
- Errors logged and raised
- No fallback
- Conversation history lost
- Caller must handle

### Caching

**Error Handling:**
- Errors logged and raised
- No fallback
- Cache misses handled gracefully

**Evidence:**
- Rate limiting in `apps/backend/app/middleware/`
- Short-term memory in `apps/backend/app/ai/memory_engine/short_term.py`

## Database Outages

### PostgreSQL

**Authentication:**
- Health check fails
- Returns 503 on readiness check
- User cannot authenticate
- No automatic retry

**Audit Logs:**
- Compliance events cannot be written
- Errors logged
- No fallback

**Evidence:**
- Health check in `apps/backend/app/main.py`

### MongoDB

**Domain Models:**
- Health check fails
- Returns 503 on readiness check
- CRUD operations fail
- No automatic retry

**Vector Metadata:**
- Memory links cannot be stored
- Document metadata cannot be stored
- Errors logged

**Evidence:**
- Health check in `apps/backend/app/main.py`

### Qdrant

**Long-Term Memory:**
- Health check fails
- Returns 503 on readiness check
- Vector search fails
- No automatic retry

**Knowledge Retrieval:**
- Document chunks cannot be retrieved
- RAG falls back to memory-only
- Errors logged

**Evidence:**
- Health check in `apps/backend/app/main.py`

## Global Exception Handler

### Implementation

**Location:** `apps/backend/app/main.py`

**Behavior:**
- Catches all unhandled exceptions
- Logs exception server-side with full context
- Includes request ID from contextvars
- Returns safe error response to client
- Only exposes stack traces in development

**Response:**
```json
{
  "success": false,
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "An unexpected error occurred on the server.",
    "details": "Exception details (development only)"
  },
  "meta": {
    "requestId": "uuid",
    "timestamp": 1234567890
  }
}
```

**Evidence:**
- Global exception handler in `apps/backend/app/main.py`

## Error Logging

### Server-Side Logging

**Implementation:**
- Structured logging with full context
- Exception logged with exc_info=True
- Request ID included in all error logs
- Error type and message logged
- Method and path logged
- Error category logged

**Fields:**
- event: "exception"
- request_id: UUID
- error_type: Exception class name
- error_message: Exception message
- method: HTTP method
- path: Request path
- error_category: Error category

**Evidence:**
- Global exception handler in `apps/backend/app/main.py`
- Logging configuration in `apps/backend/app/core/logging_config.py`

### Client-Side Response

**Development:**
- Full error details exposed
- Stack traces included
- Debug information available

**Production:**
- Generic error message only
- No stack traces
- No implementation details
- Request ID for correlation

**Evidence:**
- Global exception handler in `apps/backend/app/main.py`
- Configuration check for APP_ENV

## Known Limitations

1. **No Retry Policies:** No automatic retry for external services
2. **No Circuit Breakers:** No circuit breaker pattern for external services
3. **No Background Job Failure Handling:** Celery configured but no failure handling
4. **No Timeout Configuration:** No explicit timeouts for AI providers
5. **No Dead Letter Queue:** No queue for failed background jobs
6. **Limited Fallback:** Fallback only in AI orchestrator, not comprehensive
