# Security and Privacy

## Authentication and Session Handling

### JWT Authentication

**Implementation:**
- JWT access tokens with 15-minute expiration
- JWT refresh tokens with 7-day expiration
- Support for HS256 and RS256 algorithms
- Token rotation prevents reuse

**Token Generation:**
- Access token: Signed with JWT_SECRET (HS256) or JWT_SECRET_RS256_PRIVATE (RS256)
- Refresh token: Stored in database or token blacklist (not implemented)
- Token payload includes user_id (sub)

**Token Validation:**
- Signature validation
- Expiration check
- Token rotation (refresh token used once)
- RS256 key selection based on algorithm

**Evidence:**
- `apps/backend/app/core/security.py`
- `apps/backend/app/api/deps.py`
- `apps/backend/app/api/endpoints/auth.py`

### Session Handling

**Current State:**
- No server-side sessions
- Stateless JWT authentication
- No session store
- No session invalidation mechanism

**Planned:**
- Token blacklist for logout
- Session management for concurrent sessions
- Device fingerprinting

**Evidence:**
- No session store found
- JWT-only authentication

## Authorization and Role-Based Access Control

### RBAC Implementation

**Roles:**
- USER: Standard user role
- ADMIN: Administrator role

**Role Enforcement:**
- `require_role()` dependency factory
- Role checking against endpoint requirements
- Admin-only endpoints protected

**Implementation:**
```python
def require_role(allowed_roles: list[UserRole]):
    async def role_checker(current_user: User) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker
```

**Evidence:**
- `apps/backend/app/models/user.py` (UserRole enum)
- `apps/backend/app/api/deps.py` (require_role)

### Authorization Checks

**User Context:**
- User extracted from JWT token
- User record fetched from PostgreSQL
- Role checked against endpoint requirements
- User context propagated to handlers

**Ownership Enforcement:**
- All database queries include user_id filter
- Vector search includes user_id filter
- Tool execution enforces ownership at database level
- Cross-tenant access attempts logged

**Evidence:**
- Database queries in all repository files
- Tool registry security in `apps/backend/app/ai/tools/registry.py`
- Security tests in `test_cross_tenant_authorization.py`

## Tenant Isolation

### Database-Level Isolation

**PostgreSQL:**
- User queries always include user_id or email filter
- No cross-user queries allowed
- Role-based access for admin endpoints

**MongoDB:**
- All queries include user_id filter
- Cross-tenant access attempts logged as security events
- Generic error messages to prevent enumeration

**Evidence:**
- Database queries in `apps/backend/app/models/`
- Security tests in `test_cross_tenant_authorization.py`

### Vector Store Isolation

**Qdrant:**
- Vector search includes user_id filter
- Per-user collections or user_id payload filter
- Cross-tenant access blocked at query level
- No cross-user vector access

**Evidence:**
- Long-term memory in `apps/backend/app/ai/memory_engine/long_term.py`
- Knowledge retriever in `apps/backend/app/ai/knowledge_brain/retriever.py`

### Cache Isolation

**Redis:**
- Keys include user_id for isolation
- No cross-user key access
- Rate limiting per-user
- Short-term memory per-user

**Evidence:**
- Rate limiting in `apps/backend/app/middleware/`
- Short-term memory in `apps/backend/app/ai/memory_engine/short_term.py`

### Tool Execution Isolation

**Tool Registry:**
- All tool executors receive user_id
- Database queries include user_id filter
- Cross-tenant attempts logged as security events
- Generic error messages to prevent enumeration

**Security Events:**
- Logged to ComplianceEvent collection
- Includes user_id, event_type, resource_id, details
- Severity level tracked
- Used for compliance and audit

**Evidence:**
- Tool registry in `apps/backend/app/ai/tools/registry.py`
- Security tests in `test_tool_registry_security.py`

## Input Validation

### API Input Validation

**Pydantic Schemas:**
- All request bodies validated against Pydantic schemas
- Type checking
- Required field validation
- Custom validators
- Automatic error responses

**Evidence:**
- Schemas in `apps/backend/app/schemas/`
- FastAPI automatic validation

### Tool Argument Validation

**JSON Schema Validation:**
- Tool arguments validated against JSON schemas
- Required field checking
- Type validation
- Unexpected field rejection
- Argument size validation

**Implementation:**
```python
def _validate_arguments(self, schema: ToolSchema, arguments: Dict[str, Any]) -> None:
    # Check required fields
    for field in schema.required:
        if field not in arguments:
            raise ValueError(f"Missing required field: {field}")
    
    # Check for unexpected fields
    allowed_fields = set(schema.parameters.get("properties", {}).keys())
    for field in arguments:
        if field not in allowed_fields:
            raise ValueError(f"Unexpected field in arguments: {field}")
    
    # Type validation
    # ...
```

**Evidence:**
- Tool registry in `apps/backend/app/ai/tools/registry.py`

### AI Input Validation

**Prompt Injection Detection:**
- Regex-based detection
- Keyword-based detection
- Logs detected attempts
- Blocks suspicious inputs

**Input Sanitization:**
- Removes potentially malicious patterns
- Sanitizes before LLM processing
- Logs sanitization events

**Evidence:**
- AI security in `apps/backend/app/ai/security.py`

## Secrets Management

### Configuration Secrets

**Secrets Stored in Environment Variables:**
- SECRET_KEY: Application secret key
- JWT_SECRET: JWT signing secret
- JWT_SECRET_RS256_PRIVATE: RS256 private key
- JWT_SECRET_RS256_PUBLIC: RS256 public key
- GROQ_API_KEY: Groq API key
- GEMINI_API_KEY: Gemini API key
- OPENAI_API_KEY: OpenAI API key
- COHERE_API_KEY: Cohere API key
- ELEVENLABS_API_KEY: ElevenLabs API key
- Database passwords in connection URLs

**Secret Validation:**
- Rejects known placeholder secrets in production
- Validates secret key length (32+ characters)
- Validates SECRET_KEY and JWT_SECRET are different
- Checks for localhost in production URLs
- Checks for localhost in CORS origins

**Placeholder Secrets Rejected:**
- test_secret_key_do_not_use_in_production
- test_jwt_secret_do_not_use_in_production
- test_groq_api_key_replace_before_production
- test_gemini_api_key_replace_before_production
- lumenly (default database password)
- change_me_in_production
- Any secret with "test_" prefix and < 50 characters
- Any secret with "replace_before_production"
- Any secret with "do_not_use_in_production"

**Evidence:**
- Configuration validation in `apps/backend/app/core/config.py`

### Environment Configuration

**Environment-Specific Validation:**
- Development: Flexible configuration, warnings for obvious issues
- Test: Deterministic configuration, no strict validation
- Staging: Production-like behavior, rate limiting required
- Production: Strict requirements, all validations enforced

**Production Requirements:**
- APP_DEBUG must be False
- RATE_LIMIT_ENABLED must be True
- RATE_LIMIT_FAIL_OPEN must be False
- SECRET_KEY must be 32+ characters
- JWT_SECRET must be 32+ characters
- SECRET_KEY and JWT_SECRET must be different
- No localhost in infrastructure URLs
- No localhost in CORS origins
- At least one LLM API key must be set
- RS256 keys required if JWT_ALGORITHM=RS256

**Evidence:**
- Configuration validation in `apps/backend/app/core/config.py`

## Sensitive-Data Handling

### Data at Rest

**PostgreSQL:**
- Encryption depends on provider (PostgreSQL encryption-at-rest)
- Passwords bcrypt hashed (one-way)
- No PII in plain text (except email)

**MongoDB:**
- Encryption-at-rest via MongoDB Atlas
- No PII in vector payloads (user_id only)
- Journal content may contain sensitive information

**Redis:**
- No encryption by default
- Short-term memory may contain sensitive conversation history
- Encryption depends on deployment

**Qdrant:**
- Encryption-at-rest via Qdrant or deployment
- Vector payloads contain hashed identifiers only
- No PII in vector payloads

**Evidence:**
- Database configurations in `apps/backend/app/db/`
- No encryption configuration found in code

### Data in Transit

**HTTP/WebSocket:**
- TLS encryption depends on deployment
- No TLS configuration verified in code
- Depends on reverse proxy or load balancer

**Database Connections:**
- TLS depends on connection string configuration
- Not verified in current implementation

**Evidence:**
- No TLS configuration found
- Depends on deployment infrastructure

### Logging

**Structured Logging:**
- Request IDs for correlation
- Error logging with full context server-side
- No PII in logs (user_id only)
- Stack traces only in development

**Safe Error Messages:**
- Generic error messages to clients
- No stack traces in production
- No implementation details exposed
- Request ID for correlation

**Evidence:**
- Logging configuration in `apps/backend/app/core/logging_config.py`
- Global exception handler in `apps/backend/app/main.py`

## AI-Provider Data Flows

### LLM Providers

**Data Sent to Providers:**
- User queries (after sanitization)
- System prompts (no PII)
- Retrieved context (user-specific)
- Conversation history (last N turns)

**Data Received from Providers:**
- Generated responses
- Token usage metrics
- Model information

**Data Not Sent:**
- User email
- User personal information
- User passwords
- Internal system details

**Evidence:**
- LLM providers in `apps/backend/app/ai/llm/`
- AI security in `apps/backend/app/ai/security.py`

### Embedding Providers

**Data Sent to Providers:**
- Text chunks for embedding
- No PII in text chunks (user content only)

**Data Received from Providers:**
- Embedding vectors
- Model information

**Data Not Sent:**
- User metadata
- User identifiers
- System prompts

**Evidence:**
- Embedding providers in `apps/backend/app/ai/embeddings/`

## Logging and Telemetry Privacy

### Logging Privacy

**What is Logged:**
- Request IDs
- HTTP methods and paths
- Status codes
- Error types and messages
- User IDs (for correlation)
- Timing information

**What is Not Logged:**
- Request bodies (except in development)
- Response bodies (except in development)
- User passwords
- API keys
- PII beyond user_id

**Development vs Production:**
- Development: Full context including stack traces
- Production: Generic error messages only

**Evidence:**
- Logging configuration in `apps/backend/app/core/logging_config.py`
- Global exception handler in `apps/backend/app/main.py`

### Telemetry Privacy

**Metrics Collected:**
- HTTP request counts and durations
- Rate limit violations
- Security events (authorization failures, cross-tenant attempts)
- WebSocket connection counts
- Database health status

**Metrics Not Collected:**
- User-specific metrics
- PII in metrics
- Request content
- Response content

**Evidence:**
- Metrics in `apps/backend/app/core/metrics.py`

## Dependency and Vulnerability Checks

### Current Status

**TruffleHog:**
- Secret scanning in CI workflow
- Only verified secrets
- Scans entire repository
- Runs on every push and PR

**Evidence:**
- CI workflow in `.github/workflows/ci.yml`

**Known Limitations:**
- No dependency vulnerability scanning (npm-audit, pip-audit, etc.)
- No container vulnerability scanning
- No SAST (Static Application Security Testing)
- No DAST (Dynamic Application Security Testing)

**Evidence:**
- No vulnerability scanning beyond TruffleHog

## Rate Limiting and Abuse Prevention

### Rate Limiting Implementation

**Redis-Based:**
- Sliding window algorithm
- Distributed across workers
- Per-user and per-IP isolation
- Configurable fail-closed/fail-open

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

### Trusted Proxy Validation

**X-Forwarded-For Handling:**
- Ignored unless trusted proxy configured
- CIDR range support for trusted proxies
- Client IP fallback when proxy not trusted
- Prevents IP spoofing

**Configuration:**
- RATE_LIMIT_TRUSTED_PROXIES: Comma-separated CIDR ranges
- Empty string = no trusted proxies (ignore X-Forwarded-For)

**Evidence:**
- Trusted proxy validation in `apps/backend/app/middleware/endpoint_rate_limit.py`

### Abuse Prevention

**WebSocket Security:**
- Message size limits (10,000 characters)
- Tool argument size limits (5,000 characters)
- Connection rate limits (10 per hour)
- Message rate limits (60 per minute)
- Tool call rate limits (10 per minute)

**Evidence:**
- WebSocket security in `apps/backend/app/api/endpoints/coaching.py`

## Proxy Trust Configuration

### Trusted Proxy Configuration

**Purpose:**
- Validate X-Forwarded-For headers
- Prevent IP spoofing
- Support load balancers and proxies

**Configuration:**
- RATE_LIMIT_TRUSTED_PROXIES: Comma-separated CIDR ranges
- Example: "10.0.0.0/8,172.16.0.0/12"
- Empty = no trusted proxies

**Behavior:**
- If proxy is trusted: Use X-Forwarded-For for client IP
- If proxy is not trusted: Use direct connection IP
- If no X-Forwarded-For: Use direct connection IP

**Evidence:**
- Trusted proxy validation in `apps/backend/app/middleware/endpoint_rate_limit.py`

## Error-Message Information Disclosure

### Safe Error Messages

**Development:**
- Full error details exposed
- Stack traces included
- Debug information available

**Production:**
- Generic error messages only
- No stack traces
- No implementation details
- Request ID for correlation

**Examples:**

**Development Error:**
```json
{
  "success": false,
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "An unexpected error occurred on the server.",
    "details": "ValueError: Invalid input 'x' for field 'status'"
  },
  "meta": {
    "requestId": "uuid",
    "timestamp": 1234567890
  }
}
```

**Production Error:**
```json
{
  "success": false,
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "An unexpected error occurred on the server.",
    "details": null
  },
  "meta": {
    "requestId": "uuid",
    "timestamp": 1234567890
  }
}
```

**Evidence:**
- Global exception handler in `apps/backend/app/main.py`

## Data Retention and Deletion Behavior

### Implemented Retention

**AI Insights:**
- 90-day TTL via expires_at field
- MongoDB TTL index on expires_at
- Automatic expiration

**Rate Limiting:**
- Redis keys expire after window + 10 seconds
- Automatic cleanup

**Compliance Events:**
- No TTL (indefinite retention for compliance)

### Not Implemented

**User Data Deletion (GDPR):**
- No right-to-be-forgotten endpoint
- No data deletion process
- No data retention policy enforcement

**Journal Entries:**
- No TTL (indefinite retention)
- Planned 180-day retention (not implemented)

**Conversation History:**
- No TTL (indefinite retention in Redis)
- No archival process

**Documents:**
- No TTL (indefinite retention)
- No archival process

**Evidence:**
- TTL index on ai_insights in `apps/backend/app/models/domain.py`
- No deletion endpoints found

## Security Testing

### Security Tests

**Authentication Security:**
- `test_auth.py` (29 tests)
- Token validation
- Token expiration
- Token rotation

**Authorization Security:**
- `test_cross_tenant_authorization.py` (20+ tests)
- Cross-tenant isolation
- Role-based access control
- Ownership enforcement

**Tool Registry Security:**
- `test_tool_registry_security.py`
- Tool authorization
- Tool argument validation
- Unregistered tool prevention

**Tool Security Tenant Isolation:**
- `test_tool_security_tenant_isolation.py`
- Tool execution isolation
- Cross-tenant access prevention
- Security event logging

**Coaching Security:**
- `test_coaching_security_validation.py`
- `test_coaching_websocket_security.py`
- `test_coaching_websocket_adversarial.py`

**Evidence:**
- Security test files in `apps/backend/tests/`

### Security Validation

**Configuration Validation:**
- Rejects placeholder secrets in production
- Validates secret key length
- Validates environment contracts
- Checks for localhost in production

**AI Security Validation:**
- Prompt injection detection
- Input sanitization
- Output filtering
- User access validation

**Evidence:**
- Configuration validation in `apps/backend/app/core/config.py`
- AI security in `apps/backend/app/ai/security.py`

## Incident Response and Remediation Procedures

### Current Status

**Not Implemented:**
- No incident response plan documented
- No security incident escalation procedure
- No security event triage process
- No incident response runbooks

**Security Event Logging:**
- ComplianceEvent collection for security events
- Logs cross-tenant access attempts
- Logs authorization failures
- Logs tool authorization failures

**Evidence:**
- ComplianceEvent model in `apps/backend/app/models/domain.py`
- Tool registry security logging
- No incident response documentation

## Known Security Limitations

1. **No Data Deletion:** GDPR right-to-be-forgotten not implemented
2. **No TLS Verification:** Encryption in transit depends on deployment
3. **No Redis Encryption:** No encryption by default
4. **No Vulnerability Scanning:** No dependency or container scanning
5. **No Incident Response:** No incident response procedures
6. **No Session Management:** No server-side sessions or invalidation
7. **No Security Monitoring:** No SIEM or security monitoring
8. **No Penetration Testing:** No regular penetration testing
