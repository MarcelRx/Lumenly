# Testing and Evaluation

## Test Categories and Purposes

### Unit Tests

**Purpose:** Test individual functions and classes in isolation

**Coverage:**
- AI component interfaces (LLM, embeddings)
- Business logic in services
- Utility functions
- Model validation

**Evidence:**
- Test files in `apps/backend/tests/`
- Specific unit tests in `test_ai_llm_interface.py`, `test_ai_memory_schema.py`

### Integration Tests

**Purpose:** Test interactions between components

**Coverage:**
- Database interactions (PostgreSQL, MongoDB, Redis, Qdrant)
- API endpoint integration
- AI component integration
- Memory integration

**Evidence:**
- Integration tests in `test_memory_integration.py`, `test_rag_orchestrator.py`
- Database connection tests in conftest.py

### Security Tests

**Purpose:** Verify security controls and tenant isolation

**Coverage:**
- Authentication and authorization
- Cross-tenant isolation
- Tool registry security
- Rate limiting security
- WebSocket security

**Evidence:**
- `test_auth.py` (29 tests)
- `test_cross_tenant_authorization.py` (20+ tests)
- `test_tool_registry_security.py`
- `test_tool_security_tenant_isolation.py`
- `test_coaching_security_validation.py`
- `test_coaching_websocket_security.py`
- `test_coaching_websocket_adversarial.py`

### Rate Limiting Tests

**Purpose:** Verify rate limiting behavior

**Coverage:**
- Global rate limiting
- Endpoint-specific rate limiting
- Multi-worker rate limiting
- WebSocket rate limiting
- Redis failure behavior

**Evidence:**
- `test_rate_limiting.py`
- `test_ai_document_rate_limiting.py` (6 tests)
- `test_auth_rate_limiting.py` (8 tests)
- `test_multi_worker_rate_limiting.py` (8 tests)
- `test_rate_limit_http_contract.py` (9 tests)

### Coaching Tests

**Purpose:** Verify coaching flows and WebSocket behavior

**Coverage:**
- Coaching session flows
- WebSocket connections
- WebSocket messaging
- Coaching integration

**Evidence:**
- `test_coaching_integration.py`
- `test_coaching_websocket_adversarial.py`
- `test_coaching_websocket_security.py`

### Architecture Regression Tests

**Purpose:** Verify architectural constraints are not violated

**Coverage:**
- Component boundaries
- Dependency rules
- Security boundaries
- Data flow constraints

**Evidence:**
- `test_architecture_regression.py`
- `test_coaching_architecture_regression.py`

## Actual Test Commands

### Running All Tests

```bash
cd apps/backend
python -m pytest tests/ -v --tb=short --no-header
```

**Expected Output (Phase 12.5):**
```
832 passed, 1 xfailed, 229 warnings in 778.40s (0:12:58)
```

**Evidence:**
- Phase 12.5 report, commit 4a93c03
- CI workflow in `.github/workflows/ci.yml`

### Running Tests with Coverage

```bash
cd apps/backend
python -m pytest tests/ --cov=app --cov-report=xml --cov-report=term
```

**Evidence:**
- CI workflow in `.github/workflows/ci.yml`

### Running Specific Test Categories

```bash
# Security tests only
python -m pytest tests/test_auth.py tests/test_cross_tenant_authorization.py -v

# Rate limiting tests only
python -m pytest tests/test_rate_limiting.py tests/test_ai_document_rate_limiting.py tests/test_auth_rate_limiting.py tests/test_multi_worker_rate_limiting.py -v

# Coaching tests only
python -m pytest tests/test_coaching_integration.py tests/test_coaching_websocket_*.py -v
```

## Required Services and Prerequisites

### Services Required for Tests

**PostgreSQL:**
- Version: 15-alpine
- Port: 5433 (mapped from 5432)
- Database: lumenly_test
- User: lumenly
- Password: lumenly_secure_password_32chars

**MongoDB:**
- Version: 7
- Port: 27017
- Database: lumenly_test

**Redis:**
- Version: 7-alpine
- Port: 6379
- Database: 1

**Qdrant:**
- Version: latest
- Port: 6333
- No authentication required for local

**Evidence:**
- CI workflow service definitions in `.github/workflows/ci.yml`
- Docker Compose configuration in `infra/docker-compose.yml`

### Environment Variables Required

**Authentication:**
- `SECRET_KEY`: Test secret key (32+ characters)
- `JWT_SECRET`: Test JWT secret (32+ characters)
- `JWT_SECRET_RS256_PRIVATE`: Test RS256 private key
- `JWT_SECRET_RS256_PUBLIC`: Test RS256 public key

**Database URLs:**
- `POSTGRES_URL`: postgresql+asyncpg://lumenly:lumenly_secure_password_32chars@localhost:5433/lumenly_test
- `MONGODB_URL`: mongodb://localhost:27017/lumenly_test
- `REDIS_URL`: redis://localhost:6379/1
- `QDRANT_URL`: http://localhost:6333

**AI Provider Keys (can be empty for tests):**
- `GROQ_API_KEY`: "" (empty for tests)
- `GEMINI_API_KEY`: "" (empty for tests)
- `OPENAI_API_KEY`: "" (empty for tests)
- `COHERE_API_KEY`: "" (empty for tests)
- `ELEVENLABS_API_KEY`: "" (empty for tests)

**Evidence:**
- CI workflow environment variables in `.github/workflows/ci.yml`
- Test environment configuration in `apps/backend/.env.test`

## Test Environment Configuration

### Test Configuration

**Location:** `apps/backend/pyproject.toml`

**Settings:**
- Test paths: `["tests"]`
- Asyncio mode: `auto`
- Default fixture loop scope: `function`
- Python files: `test_*.py`
- Python classes: `Test*`
- Python functions: `test_*`
- Custom markers: `rate_limit_test`

**Evidence:**
- `apps/backend/pyproject.toml`

### Test Fixtures

**Location:** `apps/backend/tests/conftest.py`

**Fixtures Provided:**
- Database sessions (PostgreSQL, MongoDB)
- Redis client
- Qdrant client
- Test users
- Authentication tokens
- AI providers (mock)
- Embedding providers (mock)
- Memory manager
- Tool registry

**Evidence:**
- `apps/backend/tests/conftest.py` (20590 bytes)

## Unit, Integration, API Contract, Security, and End-to-End Testing

### Unit Testing

**Coverage:**
- LLM interface: `test_ai_llm_interface.py`
- Memory schema: `test_ai_memory_schema.py`
- Configuration validation
- Utility functions

**Evidence:**
- Test files in `apps/backend/tests/`

### Integration Testing

**Coverage:**
- Memory integration: `test_memory_integration.py`
- RAG orchestrator: `test_rag_orchestrator.py`
- Coaching integration: `test_coaching_integration.py`
- Database integration (all tests use real databases)

**Evidence:**
- Integration test files in `apps/backend/tests/`

### API Contract Testing

**Coverage:**
- Rate limiting HTTP contract: `test_rate_limit_http_contract.py` (9 tests)
- API endpoint contracts (implicit in endpoint tests)

**Evidence:**
- `test_rate_limit_http_contract.py`

### Security Testing

**Coverage:**
- Authentication: `test_auth.py` (29 tests)
- Cross-tenant authorization: `test_cross_tenant_authorization.py` (20+ tests)
- Tool registry security: `test_tool_registry_security.py`
- Tool security tenant isolation: `test_tool_security_tenant_isolation.py`
- Coaching security validation: `test_coaching_security_validation.py`
- Coaching WebSocket security: `test_coaching_websocket_security.py`
- Coaching WebSocket adversarial: `test_coaching_websocket_adversarial.py`

**Evidence:**
- Security test files in `apps/backend/tests/`

### End-to-End Testing

**Coverage:**
- Limited E2E testing
- Most tests are integration-level
- No full-stack E2E tests with frontend

**Evidence:**
- No E2E test files found

## AI Evaluation Methods and Evaluation Limitations

### Current Evaluation

**Manual Testing:**
- Manual testing through test suite
- No automated evaluation framework
- No human evaluation metrics

**Test Coverage:**
- 832 tests passing
- 1 xfailed test (expected failure)
- 229 warnings (non-blocking)

**Evidence:**
- Phase 12.5 report
- Test suite in `apps/backend/tests/`

### Evaluation Limitations

**No Automated Evaluation:**
- No automated quality metrics
- No hallucination rate measurement
- No retrieval precision measurement
- No user satisfaction metrics

**No A/B Testing:**
- No A/B testing infrastructure
- No prompt versioning for experiments
- No automated comparison between variants

**No Human Evaluation:**
- No human evaluation process
- No quality scoring system
- No feedback collection

**Evidence:**
- No evaluation framework code found
- No A/B testing infrastructure found

## CI Workflows and Required Checks

### CI Workflow

**Location:** `.github/workflows/ci.yml`

**Jobs:**
1. **Test:** Run tests with service dependencies
2. **Lint:** Run Ruff linter and formatter
3. **Security Scan:** Run TruffleHog for secret scanning
4. **Build:** Build Docker image

**Triggers:**
- Push to main or develop branches
- Pull requests to main or develop branches

**Evidence:**
- `.github/workflows/ci.yml`

### Required Checks

**Test Job:**
- Service connectivity verification (PostgreSQL, MongoDB, Redis, Qdrant)
- Full test suite execution
- Coverage reporting

**Lint Job:**
- Ruff check with auto-fix
- Ruff format

**Security Scan Job:**
- TruffleHog secret scanning
- Only verified secrets

**Build Job:**
- Docker image build
- Docker image test

**Evidence:**
- CI workflow definition in `.github/workflows/ci.yml`

## Failure Investigation Procedures

### Test Failures

**Procedure:**
1. Check test output for error messages
2. Review test logs in CI
3. Run tests locally with verbose output
4. Check service health (PostgreSQL, MongoDB, Redis, Qdrant)
5. Review recent code changes
6. Check for environment configuration issues

**Evidence:**
- CI workflow logs
- Test execution in local environment

### Service Failures

**Procedure:**
1. Check service logs
2. Verify service connectivity
3. Check service health endpoints
4. Review service configuration
5. Restart services if needed

**Evidence:**
- Health check endpoints in `apps/backend/app/main.py`
- Service health checks in CI workflow

### Rate Limiting Failures

**Procedure:**
1. Check Redis connectivity
2. Verify Redis key patterns
3. Check rate limit configuration
4. Review rate limit middleware logs
5. Test rate limiting manually

**Evidence:**
- Rate limiting tests in `apps/backend/tests/`
- Rate limiting middleware in `apps/backend/app/middleware/`

## Known Flaky or Skipped Tests

### XFailed Tests

**test_configuration.py:**
- 1 xfailed test (expected failure)
- Reason: Configuration validation test for specific scenario
- Not a flaky test, intentionally marked as xfailed

**Evidence:**
- Phase 12.5 report: "1 xfailed"

### Flaky Tests

**Current Status:**
- No known flaky tests reported
- 229 warnings but no flaky tests

**Warnings:**
- 169 PytestWarnings: asyncio marks on non-async functions (cosmetic)
- 50+ DeprecationWarnings: Third-party library deprecations
- 10+ SecurityWarnings: JWT key length warnings in test fixtures

**Evidence:**
- Phase 12.5 report
- Test warnings in test output

## Expected Failures and Their Documented Reasons

### Expected Failure

**test_configuration.py:**
- Expected failure for specific configuration validation scenario
- Documented in test file
- Not a bug, intentional test behavior

**Evidence:**
- Phase 12.5 report: "1 xfailed"

## Untested Areas and Known Verification Gaps

### Untested Areas

**Voice Pipeline:**
- Not implemented, therefore not tested

**Wellness Intelligence Engine:**
- Not implemented, therefore not tested

**Personalization Engine:**
- Not implemented, therefore not tested

**Concrete Agent Implementations:**
- Not implemented, therefore not tested

**Data Deletion (GDPR):**
- Not implemented, therefore not tested

**Circuit Breakers:**
- Not implemented, therefore not tested

**End-to-End with Frontend:**
- No E2E tests with frontend

**Evidence:**
- No test files for these components
- Architecture documentation confirms not implemented

### Verification Gaps

**AI Quality:**
- No automated quality metrics
- No hallucination rate measurement
- No retrieval precision measurement

**Performance:**
- No load testing
- No performance benchmarks (except basic metrics)
- No response time SLA verification

**Security:**
- No penetration testing
- No vulnerability scanning beyond TruffleHog
- No dependency vulnerability scanning

**Evidence:**
- No performance test files found
- No security scanning beyond TruffleHog

## Links to Authoritative Evidence

### Test Results

**Phase 12.5 Report:**
- File: `PHASE_12_5_FINAL_REPORT.md`
- Commit: 4a93c03634519e77d905110a4c5b5106bcd2b774
- Date: 2026-10-16
- Results: 832 passed, 1 xfailed, 229 warnings in 778.40s

**Evidence:**
- `PHASE_12_5_FINAL_REPORT.md` in repository root

### CI Workflow

**Location:** `.github/workflows/ci.yml`

**Evidence:**
- CI workflow definition

### Test Configuration

**Location:** `apps/backend/pyproject.toml`

**Evidence:**
- Pytest configuration

### Test Fixtures

**Location:** `apps/backend/tests/conftest.py`

**Evidence:**
- Test fixture definitions

## Distinguishing Passed, Failed, Skipped, XFailed, Blocked, and Not-Run Tests

### Passed Tests
- Tests that executed successfully
- 832 tests in Phase 12.5

### Failed Tests
- Tests that executed but failed assertions
- 0 tests in Phase 12.5

### Skipped Tests
- Tests marked with @pytest.mark.skip
- Count not reported in Phase 12.5

### XFailed Tests
- Tests marked with @pytest.mark.xfail (expected to fail)
- 1 test in Phase 12.5

### Blocked Tests
- Tests that could not run due to missing dependencies
- Not reported in Phase 12.5

### Not-Run Tests
- Tests not collected or executed
- Not reported in Phase 12.5

**Evidence:**
- Phase 12.5 report
- Pytest documentation

## Current Test Results (As of Phase 12.5)

**Total Tests:** 833 collected
**Passed:** 832
**Failed:** 0
**XFailed:** 1
**Warnings:** 229
**Execution Time:** 778.40s (12:58)

**Commit:** 4a93c03634519e77d905110a4c5b5106bcd2b774
**Date:** 2026-10-16
**Branch:** develop

**Evidence:**
- `PHASE_12_5_FINAL_REPORT.md`

## Notes

- Historical Phase 12.5 results labeled as historical report
- Current results may differ if code has changed
- Re-run full suite to verify current state
- Docker must be running for tests to pass
- Services must be healthy for tests to pass
