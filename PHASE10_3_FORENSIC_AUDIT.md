# PHASE 10.3 — PRODUCTION MONITORING & ALERTING FORENSIC AUDIT

**Date:** 2026-09-01  
**Phase:** 10.3 — Production Monitoring & Alerting  
**Status:** FORENSIC AUDIT COMPLETE  
**Engineer:** Senior Production Observability / SRE Engineer

---

## EXECUTIVE SUMMARY

**DECISION:** PROCEED WITH IMPLEMENTATION

The Lumenly backend has a solid observability foundation from Phases 10.1, 10.2A, and 10.2B, including 28 production metrics, structured logging, health endpoints, and Prometheus multiprocess support. However, the **operational monitoring layer is incomplete** — Prometheus configuration needs corrections, alert rules need expansion, Alertmanager is missing, Grafana needs provisioning, and operational runbooks are absent.

### Critical Findings

**Configuration Issues:**
1. **P1 — Incorrect Metrics Path:** Root `prometheus.yml` scrapes `/api/v1/metrics` but the actual endpoint is `/v1/metrics`
2. **P2 — Outdated Alert Rules:** Existing `prometheus-alerts.yml` uses incorrect metric names (e.g., `gemini_requests_total` instead of `llm_requests_total`)

**Missing Components:**
1. **P1 — No Alertmanager Configuration:** No Alertmanager service or configuration exists
2. **P1 — No Production Alert Rules:** Existing alerts are incomplete and don't cover backend availability, dependencies, Celery, security
3. **P2 — No Grafana Provisioning:** Grafana service exists but has no dashboards or provisioning
4. **P2 — No Operational Runbooks:** No runbooks for incident response
5. **P2 — No Monitoring Test Suite:** No dedicated tests for alerting configuration

### Existing Strengths

- ✅ 28 production metrics with bounded cardinality
- ✅ Prometheus multiprocess support verified
- ✅ Structured JSON logging with secret redaction
- ✅ Request correlation via X-Request-ID
- ✅ Health endpoints integrated with metrics
- ✅ Celery metrics with synchronous architecture
- ✅ Security metrics (auth, authorization, rate limiting)
- ✅ Dependency health metrics (PostgreSQL, MongoDB, Redis, Qdrant)
- ✅ LLM metrics (provider, failures, latency, tokens)
- ✅ Docker Compose includes Prometheus and Grafana services

### Implementation Scope

**Required Changes:**
1. Fix Prometheus configuration (metrics path)
2. Create comprehensive alert rules (backend, dependencies, Celery, LLM, security)
3. Add Alertmanager configuration
4. Create Grafana dashboards (API, Dependencies, Celery, AI, Security)
5. Create operational runbooks
6. Create monitoring test suite
7. Runtime verification of all components

**No Changes Required:**
- Metrics implementation (already production-ready)
- Logging configuration (already production-ready)
- Health endpoints (already production-ready)
- Celery architecture (already verified synchronous)
- Cardinality protection (already verified)

---

## EXISTING OBSERVABILITY COMPONENTS

### 1. Prometheus Configuration

**Location:** `/Users/mohsenrassam/Desktop/Lumenly/prometheus.yml`

**Current Configuration:**
```yaml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: fastapi
    metrics_path: /api/v1/metrics  # ❌ INCORRECT - should be /v1/metrics
    static_configs:
      - targets:
          - host.docker.internal:8000
```

**Issues:**
- ❌ Incorrect metrics path: `/api/v1/metrics` should be `/v1/metrics`
- ❌ No alert rule files configured
- ❌ No recording rules configured
- ❌ No scrape timeout configured
- ❌ No target health monitoring configured

**Required Fixes:**
- Correct metrics path to `/v1/metrics`
- Add alert rule files
- Add recording rules where beneficial
- Configure scrape timeout
- Add target health monitoring

---

### 2. Existing Alert Rules

**Location:** `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/monitoring/prometheus-alerts.yml`

**Current Alerts:**
```yaml
groups:
  - name: lumenly-backend-alerts
    rules:
      - alert: HighRAGResponseLatency
        expr: histogram_quantile(0.95, rate(rag_response_latency_seconds_bucket[5m])) > 5.0
        # ❌ Metric doesn't exist - should use http_request_duration_seconds

      - alert: GeminiAPIHighLatency
        expr: histogram_quantile(0.95, rate(gemini_api_latency_seconds_bucket[5m])) > 3.0
        # ❌ Metric doesn't exist - should use llm_request_duration_seconds

      - alert: HighGeminiErrorRate
        expr: rate(gemini_requests_failure_total[5m]) / rate(gemini_requests_total[5m]) > 0.1
        # ❌ Metric doesn't exist - should use llm_request_failures_total

      - alert: RateLimitExceeded
        expr: rate(rag_response_latency_seconds_count[1m]) > 15
        # ❌ Wrong metric - should use rate_limit_violations_total
```

**Issues:**
- ❌ All alerts use non-existent metric names
- ❌ No backend availability alerts
- ❌ No dependency failure alerts
- ❌ No Celery alerts
- ❌ No security alerts
- ❌ No severity labels (P0/P1/P2/P3)
- ❌ No runbook references
- ❌ No proper alert grouping

**Required Changes:**
- Rewrite all alerts to use correct metric names
- Add backend availability alerts (P0)
- Add dependency failure alerts (P0/P1)
- Add Celery alerts (P1/P2)
- Add security alerts (P1/P2)
- Add severity model (P0/P1/P2/P3)
- Add runbook references
- Add proper alert grouping

---

### 3. Docker Compose Configuration

**Location:** `/Users/mohsenrassam/Desktop/Lumenly/.docker/docker-compose.yml`

**Existing Services:**
```yaml
services:
  postgres:      # ✅ Present
  mongo:         # ✅ Present
  redis:         # ✅ Present
  qdrant:        # ✅ Present
  prometheus:    # ✅ Present
  grafana:       # ✅ Present
  backend:       # ✅ Present
  celery-worker: # ✅ Present
```

**Monitoring Services:**
```yaml
prometheus:
  image: prom/prometheus:latest
  container_name: lumenly-prometheus
  ports:
    - "9090:9090"
  volumes:
    - ../prometheus.yml:/etc/prometheus/prometheus.yml:ro
  # ❌ No rule files mounted
  # ❌ No alertmanager configured
  # ❌ No persistent storage

grafana:
  image: grafana/grafana:latest
  container_name: lumenly-grafana
  depends_on:
    - prometheus
  ports:
    - "3000:3000"
  # ❌ No provisioning configured
  # ❌ No dashboards mounted
  # ❌ No persistent storage
```

**Issues:**
- ❌ Prometheus: No rule files mounted
- ❌ Prometheus: No Alertmanager configured
- ❌ Prometheus: No persistent storage
- ❌ Grafana: No provisioning configured
- ❌ Grafana: No dashboards mounted
- ❌ Grafana: No persistent storage
- ❌ No Alertmanager service

**Required Additions:**
- Mount Prometheus rule files
- Configure Alertmanager in Prometheus
- Add persistent storage for Prometheus
- Add Grafana provisioning
- Mount Grafana dashboards
- Add persistent storage for Grafana
- Add Alertmanager service

---

### 4. Metrics Implementation

**Location:** `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/app/core/metrics.py`

**Status:** ✅ PRODUCTION-READY (No changes required)

**Metrics Inventory (28 total):**

| Metric | Type | Labels | Status |
|--------|------|--------|--------|
| `http_requests_total` | Counter | method, route, status_code | ✅ Safe |
| `http_request_duration_seconds` | Histogram | method, route, status_code | ✅ Safe |
| `http_requests_in_flight` | Gauge | method | ✅ Safe |
| `auth_login_attempts_total` | Counter | result | ✅ Safe |
| `auth_token_refresh_total` | Counter | result | ✅ Safe |
| `auth_registration_attempts_total` | Counter | result | ✅ Safe |
| `security_authorization_failures_total` | Counter | resource_type | ✅ Safe |
| `security_cross_tenant_attempts_total` | Counter | resource_type | ✅ Safe |
| `security_rate_limit_exceeded_total` | Counter | endpoint, user_role | ✅ Safe |
| `database_health_status` | Gauge | database | ✅ Safe |
| `database_operation_failures_total` | Counter | database, operation_type | ✅ Safe |
| `celery_tasks_total` | Counter | task, status | ✅ Safe |
| `celery_task_failures_total` | Counter | task, failure_type | ✅ Safe |
| `celery_task_retries_total` | Counter | task | ✅ Safe |
| `celery_task_duration_seconds` | Histogram | task | ✅ Safe |
| `llm_requests_total` | Counter | provider, model | ✅ Safe |
| `llm_request_failures_total` | Counter | provider, failure_type | ✅ Safe |
| `llm_request_duration_seconds` | Histogram | provider | ✅ Safe |
| `llm_input_tokens_total` | Counter | provider | ✅ Safe |
| `llm_output_tokens_total` | Counter | provider | ✅ Safe |
| `websocket_connections_total` | Counter | result | ✅ Safe |
| `websocket_disconnects_total` | Counter | reason | ✅ Safe |
| `websocket_messages_total` | Counter | message_type, direction | ✅ Safe |
| `websocket_message_failures_total` | Counter | failure_type | ✅ Safe |
| `websocket_active_connections` | Gauge | (none) | ✅ Safe |
| `document_processing_total` | Counter | status | ✅ Safe |
| `document_processing_duration_seconds` | Histogram | status | ✅ Safe |
| `vector_ingestion_failures_total` | Counter | failure_type | ✅ Safe |
| `rate_limit_violations_total` | Counter | limit_type, user_role | ✅ Safe |

**Cardinality Status:** ✅ LOW (all labels bounded)  
**Security Status:** ✅ SECURE (no sensitive data in labels)  
**Multiprocess Status:** ✅ VERIFIED (Phase 10.2B)

---

### 5. Logging Configuration

**Location:** `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/app/core/logging_config.py`

**Status:** ✅ PRODUCTION-READY (No changes required)

**Capabilities:**
- ✅ Structured JSON logging for production
- ✅ Request correlation via X-Request-ID
- ✅ Secret redaction patterns (passwords, API keys, JWTs, tokens)
- ✅ Contextvar-based async-safe propagation
- ✅ Environment-based configuration
- ✅ Standardized log fields (timestamp, level, logger, service, environment, request_id)

**Secret Redaction Patterns:**
- passwords
- api_keys
- jwt
- tokens
- authorization headers
- secrets
- Bearer tokens
- OpenAI-style API keys (sk-*)
- Google-style API keys (AIza*)

---

### 6. Health Endpoints

**Location:** `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/app/main.py`

**Status:** ✅ PRODUCTION-READY (No changes required)

**Endpoints:**
- `/health/live` - Liveness probe (process alive, no dependencies)
- `/health/ready` - Readiness probe (checks PostgreSQL, MongoDB, Redis, Qdrant)
- `/health` - Legacy endpoint (backward compatibility)

**Integration with Metrics:**
- ✅ `/health/ready` updates `database_health_status` metrics in real-time
- ✅ Each dependency check sets corresponding gauge to 1 (healthy) or 0 (unhealthy)
- ✅ Timeout protection (5 second timeout per dependency)
- ✅ Returns 503 Service Unavailable when any dependency is unhealthy

---

### 7. Celery Configuration

**Location:** `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/app/core/celery_app.py`

**Status:** ✅ PRODUCTION-READY (No changes required)

**Architecture:**
- ✅ Synchronous task implementation (as approved in Phase 10.2B)
- ✅ Separate Prometheus registry for worker metrics
- ✅ Task routing by queue (document_processing, memory_operations, coaching_operations)
- ✅ Retry logic (task_acks_late, task_reject_on_worker_lost)
- ✅ Fair task distribution (worker_prefetch_multiplier=1)

**Metrics Integration:**
- ✅ `celery_tasks_total` - task executions by status
- ✅ `celery_task_failures_total` - failures by type
- ✅ `celery_task_retries_total` - retry count
- ✅ `celery_task_duration_seconds` - task latency histogram

---

### 8. Environment Configuration

**Location:** `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/app/core/config.py`

**Status:** ✅ PRODUCTION-READY (No changes required)

**Security Validations:**
- ✅ Production secret validation (rejects placeholder/test secrets)
- ✅ Embedding configuration validation
- ✅ CORS validation (rejects wildcard in production)
- ✅ Rate limit fail-closed enforcement in production
- ✅ Infrastructure URL validation (no localhost in production)

**Monitoring-Relevant Settings:**
- `RATE_LIMIT_ENABLED` - Rate limiting toggle
- `RATE_LIMIT_FAIL_OPEN` - Fail open/closed behavior
- `RATE_LIMIT_REDIS_PREFIX` - Redis key prefix for rate limits
- Database URLs, Redis URL, Qdrant URL - for health checks

---

### 9. Metrics Endpoint

**Location:** `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/app/api/endpoints/metrics.py`

**Status:** ✅ PRODUCTION-READY (No changes required)

**Endpoint:** `/v1/metrics` (not `/api/v1/metrics`)

**Capabilities:**
- ✅ Multiprocess mode detection
- ✅ `MultiProcessCollector` for Uvicorn workers
- ✅ Standard Prometheus text format
- ✅ Correct content type

**Rate Limit Status:**
- ✅ `/v1/metrics` is in rate limit skip list (fixed in Phase 10.2B)

---

### 10. Metrics Middleware

**Location:** `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/app/middleware/metrics.py`

**Status:** ✅ PRODUCTION-READY (No changes required)

**Capabilities:**
- ✅ Automatic HTTP request metrics collection
- ✅ Route template extraction via `get_route_template()`
- ✅ Cardinality protection (numeric IDs → {id}, UUIDs → {uuid})
- ✅ In-flight request tracking
- ✅ Request latency histogram
- ✅ Skips health and metrics endpoints to reduce noise

**Cardinality Protection:**
- ✅ Numeric segments normalized to `{id}`
- ✅ UUID-like segments normalized to `{uuid}`
- ✅ MongoDB ObjectId-like segments normalized to `{id}`
- ✅ Long alphanumeric segments normalized to `{id}`
- ✅ Verified in Phase 10.2B runtime testing

---

## EXISTING GRAFANA DASHBOARD

**Location:** `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/monitoring/grafana-dashboard.json`

**Status:** ⚠️ BASIC - Needs expansion

**Current State:**
- Basic dashboard exists
- Likely outdated (uses old metric names)
- Not provisioned in Grafana
- No comprehensive coverage

**Required:**
- 5 comprehensive dashboards (API, Dependencies, Celery, AI, Security)
- Grafana provisioning configuration
- Dashboard JSON files with correct metric names

---

## GAPS ANALYSIS

### Critical Gaps (P0/P1)

1. **Prometheus Configuration Issues**
   - Incorrect metrics path (`/api/v1/metrics` → `/v1/metrics`)
   - No alert rule files configured
   - No recording rules
   - No Alertmanager integration

2. **Missing Alert Rules**
   - No backend availability alerts (P0)
   - No dependency failure alerts (P0/P1)
   - No Celery alerts (P1/P2)
   - No security alerts (P1/P2)
   - Existing alerts use wrong metric names

3. **No Alertmanager**
   - No Alertmanager service in Docker Compose
   - No Alertmanager configuration
   - No notification routing
   - No alert grouping/deduplication

### Important Gaps (P2)

4. **Grafana Not Provisioned**
   - No provisioning configuration
   - No dashboards mounted
   - No persistent storage
   - Existing dashboard likely outdated

5. **No Operational Runbooks**
   - No runbooks for incident response
   - No troubleshooting guides
   - No escalation procedures

6. **No Monitoring Test Suite**
   - No tests for alert configuration
   - No tests for Prometheus configuration
   - No security tests for monitoring

### Non-Critical Gaps (P3)

7. **Docker Compose Enhancements**
   - No persistent storage for monitoring services
   - No health checks for monitoring services
   - Using `:latest` tags (should pin versions)

---

## PROPOSED ARCHITECTURE

### Monitoring Stack Structure

```
monitoring/
├── prometheus/
│   ├── prometheus.yml              # Main configuration
│   ├── rules/
│   │   ├── backend.yml             # Backend availability alerts
│   │   ├── dependencies.yml        # Dependency failure alerts
│   │   ├── celery.yml              # Celery alerts
│   │   ├── security.yml            # Security alerts
│   │   └── llm.yml                 # LLM alerts
│   └── recording_rules.yml         # Recording rules (if needed)
│
├── alertmanager/
│   └── alertmanager.yml            # Alertmanager configuration
│
└── grafana/
    ├── provisioning/
    │   ├── datasources/
    │   │   └── prometheus.yml      # Prometheus datasource
    │   └── dashboards/
    │       └── dashboards.yml       # Dashboard provisioning
    └── dashboards/
        ├── api-overview.json       # API dashboard
        ├── dependencies.json       # Dependencies dashboard
        ├── celery.json             # Celery dashboard
        ├── ai-llm.json             # AI/LLM dashboard
        └── security.json           # Security dashboard
```

### Docker Compose Integration

```yaml
services:
  prometheus:
    image: prom/prometheus:v2.48.0  # Pinned version
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./monitoring/prometheus/rules:/etc/prometheus/rules:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'

  alertmanager:
    image: prom/alertmanager:v0.26.0  # Pinned version
    volumes:
      - ./monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'

  grafana:
    image: grafana/grafana:10.2.0  # Pinned version
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
```

### Alert Severity Model

**P0 — CRITICAL**
- Backend completely unavailable
- Readiness continuously failing
- Complete database outage
- Security-critical failure
- Widespread request failure

**P1 — HIGH**
- Sustained high HTTP 5xx rate (> 5% for 5 minutes)
- Severe latency degradation (p95 > 1s for 5 minutes)
- Celery workers continuously failing
- Primary LLM provider unavailable
- Major dependency degradation

**P2 — WARNING**
- Elevated latency (p95 > 500ms for 10 minutes)
- Increased task retries
- Dependency latency degradation
- Elevated authentication failures
- Unusual rate-limit activity

**P3 — INFORMATIONAL**
- Minor increases in retries
- Low-volume provider failures
- Capacity warnings

---

## SECURITY CONSIDERATIONS

### Non-Negotiable Requirements

1. **Never Expose Secrets**
   - ✅ No JWTs in metrics (verified in Phase 10.2B)
   - ✅ No passwords in metrics (verified in Phase 10.2B)
   - ✅ No API keys in metrics (verified in Phase 10.2B)
   - ✅ No user IDs in metrics (verified in Phase 10.2B)
   - ✅ No emails in metrics (verified in Phase 10.2B)
   - ✅ No document IDs in metrics (verified in Phase 10.2B)

2. **Tenant Isolation**
   - ✅ Monitoring must not weaken tenant isolation
   - ✅ No cross-tenant data in alerts
   - ✅ No tenant IDs in metric labels

3. **Metric Cardinality**
   - ✅ No unbounded labels (verified in Phase 10.2B)
   - ✅ Use route templates, not actual paths
   - ✅ Use bounded categorical values

4. **Metrics Endpoint Security**
   - ✅ `/v1/metrics` remains accessible to Prometheus
   - ✅ `/v1/metrics` is in rate limit skip list
   - ✅ No authentication required for metrics endpoint (standard practice)

### Alert Security

- ❌ No user IDs in alert labels
- ❌ No emails in alert labels
- ❌ No JWTs in alert labels
- ❌ No API keys in alert labels
- ❌ No request IDs in alert labels
- ❌ No document IDs in alert labels
- ✅ Use bounded categorical labels only

### Runbook Security

- ❌ No credentials in runbooks
- ❌ No connection strings in runbooks
- ❌ No API keys in runbooks
- ✅ Use environment variable references
- ✅ Document safe diagnostic commands only

---

## TESTING STRATEGY

### Configuration Tests

1. **Prometheus Configuration Validation**
   - Load prometheus.yml
   - Validate syntax
   - Validate rule files load
   - Validate no duplicate rule names
   - Validate metric names exist

2. **Alert Rule Validation**
   - Load all rule files
   - Validate PromQL syntax
   - Validate alert expressions
   - Validate severity labels
   - Validate runbook references

3. **Alertmanager Configuration Validation**
   - Load alertmanager.yml
   - Validate syntax
   - Validate routing rules
   - Validate no hardcoded secrets

### Security Tests

1. **No Secrets in Monitoring Configuration**
   - Scan prometheus.yml for secrets
   - Scan rule files for secrets
   - Scan alertmanager.yml for secrets
   - Scan Grafana dashboards for secrets

2. **No Sensitive Data in Alerts**
   - Verify no user IDs in alert labels
   - Verify no emails in alert labels
   - Verify no JWTs in alert labels
   - Verify bounded cardinality

3. **Metrics Endpoint Security**
   - Verify `/v1/metrics` accessible
   - Verify no secrets in metrics output
   - Verify rate limit exclusion

### Alert Semantics Tests

1. **Backend Down Alert**
   - Stop backend service
   - Verify alert fires
   - Verify severity P0
   - Restart backend
   - Verify alert resolves

2. **High 5xx Rate Alert**
   - Generate 5xx errors
   - Verify alert fires after threshold
   - Verify severity P1
   - Stop errors
   - Verify alert resolves

3. **Dependency Failure Alerts**
   - Stop PostgreSQL
   - Verify alert fires
   - Verify severity P0/P1
   - Restart PostgreSQL
   - Verify alert resolves

4. **Celery Failure Alerts**
   - Generate Celery task failures
   - Verify alert fires
   - Verify severity P1/P2
   - Stop failures
   - Verify alert resolves

5. **LLM Failure Alerts**
   - Simulate LLM provider failure
   - Verify alert fires
   - Verify severity P1
   - Restore provider
   - Verify alert resolves

6. **Security Alerts**
   - Generate authentication failures
   - Verify alert fires
   - Verify severity P1/P2
   - Stop failures
   - Verify alert resolves

### Regression Tests

1. **Metrics Endpoint Remains Accessible**
   - Verify `/v1/metrics` returns 200
   - Verify Prometheus can scrape
   - Verify no rate limit blocking

2. **Health Endpoints Still Work**
   - Verify `/health/live` returns 200
   - Verify `/health/ready` returns 200/503 appropriately
   - Verify dependency checks work

3. **Tenant Isolation Remains Intact**
   - Verify no cross-tenant data in metrics
   - Verify no tenant IDs in labels
   - Verify isolation tests still pass

4. **Authentication Remains Intact**
   - Verify JWT authentication still works
   - Verify no auth bypass via monitoring
   - Verify auth metrics still accurate

5. **Celery Remains Synchronous**
   - Verify no async/await in tasks
   - Verify sync clients still used
   - Verify architecture regression tests pass

6. **Prometheus Multiprocess Support Remains Functional**
   - Verify multiprocess mode enabled
   - Verify metrics aggregate correctly
   - Verify no metric corruption

---

## EXACT FILES REQUIRING MODIFICATION

### Files to Modify

1. **`/Users/mohsenrassam/Desktop/Lumenly/prometheus.yml`**
   - Fix metrics path: `/api/v1/metrics` → `/v1/metrics`
   - Add rule files directory
   - Add scrape timeout
   - Add Alertmanager configuration

2. **`/Users/mohsenrassam/Desktop/Lumenly/.docker/docker-compose.yml`**
   - Add Prometheus rule files volume mount
   - Add Prometheus persistent storage
   - Add Alertmanager service
   - Add Alertmanager persistent storage
   - Add Grafana provisioning volume mount
   - Add Grafana dashboards volume mount
   - Add Grafana persistent storage
   - Pin image versions (remove `:latest`)
   - Add health checks for monitoring services

3. **`/Users/mohsenrassam/Desktop/Lumenly/apps/backend/monitoring/prometheus-alerts.yml`**
   - Rewrite all alerts to use correct metric names
   - Add backend availability alerts
   - Add dependency failure alerts
   - Add Celery alerts
   - Add security alerts
   - Add severity labels
   - Add runbook references

### Files to Create

4. **`/Users/mohsenrassam/Desktop/Lumenly/monitoring/prometheus/rules/backend.yml`**
   - Backend availability alerts
   - High 5xx rate alerts
   - High latency alerts

5. **`/Users/mohsenrassam/Desktop/Lumenly/monitoring/prometheus/rules/dependencies.yml`**
   - PostgreSQL failure alerts
   - MongoDB failure alerts
   - Redis failure alerts
   - Qdrant failure alerts

6. **`/Users/mohsenrassam/Desktop/Lumenly/monitoring/prometheus/rules/celery.yml`**
   - Celery worker unavailable alerts
   - Celery task failure alerts
   - Celery retry alerts
   - Celery duration alerts

7. **`/Users/mohsenrassam/Desktop/Lumenly/monitoring/prometheus/rules/security.yml`**
   - Authentication failure alerts
   - Authorization failure alerts
   - Cross-tenant attempt alerts
   - Rate limit violation alerts

8. **`/Users/mohsenrassam/Desktop/Lumenly/monitoring/prometheus/rules/llm.yml`**
   - LLM provider failure alerts
   - LLM high latency alerts
   - LLM high error rate alerts
   - MockLLM detection alerts

9. **`/Users/mohsenrassam/Desktop/Lumenly/monitoring/alertmanager/alertmanager.yml`**
   - Alertmanager configuration
   - Routing rules
   - Notification configuration (environment variables)
   - Grouping rules
   - Inhibition rules

10. **`/Users/mohsenrassam/Desktop/Lumenly/monitoring/grafana/provisioning/datasources/prometheus.yml`**
    - Prometheus datasource configuration
    - Access mode
    - Basic auth (if needed)

11. **`/Users/mohsenrassam/Desktop/Lumenly/monitoring/grafana/provisioning/dashboards/dashboards.yml`**
    - Dashboard provisioning configuration
    - Dashboard auto-loading

12. **`/Users/mohsenrassam/Desktop/Lumenly/monitoring/grafana/dashboards/api-overview.json`**
    - API overview dashboard
    - Request rate, error rate, latency
    - In-flight requests

13. **`/Users/mohsenrassam/Desktop/Lumenly/monitoring/grafana/dashboards/dependencies.json`**
    - Dependencies dashboard
    - PostgreSQL, MongoDB, Redis, Qdrant health
    - Operation failures

14. **`/Users/mohsenrassam/Desktop/Lumenly/monitoring/grafana/dashboards/celery.json`**
    - Celery dashboard
    - Task throughput, failures, retries
    - Task duration

15. **`/Users/mohsenrassam/Desktop/Lumenly/monitoring/grafana/dashboards/ai-llm.json`**
    - AI/LLM dashboard
    - Provider usage, failures, latency
    - Token consumption

16. **`/Users/mohsenrassam/Desktop/Lumenly/monitoring/grafana/dashboards/security.json`**
    - Security dashboard
    - Auth failures, authorization failures
    - Cross-tenant attempts, rate limits

17. **`/Users/mohsenrassam/Desktop/Lumenly/docs/runbooks/backend-down.md`**
    - Backend down runbook

18. **`/Users/mohsenrassam/Desktop/Lumenly/docs/runbooks/high-error-rate.md`**
    - High error rate runbook

19. **`/Users/mohsenrassam/Desktop/Lumenly/docs/runbooks/high-latency.md`**
    - High latency runbook

20. **`/Users/mohsenrassam/Desktop/Lumenly/docs/runbooks/postgres-unavailable.md`**
    - PostgreSQL unavailable runbook

21. **`/Users/mohsenrassam/Desktop/Lumenly/docs/runbooks/mongodb-unavailable.md`**
    - MongoDB unavailable runbook

22. **`/Users/mohsenrassam/Desktop/Lumenly/docs/runbooks/redis-unavailable.md`**
    - Redis unavailable runbook

23. **`/Users/mohsenrassam/Desktop/Lumenly/docs/runbooks/qdrant-unavailable.md`**
    - Qdrant unavailable runbook

24. **`/Users/mohsenrassam/Desktop/Lumenly/docs/runbooks/celery-failures.md`**
    - Celery failures runbook

25. **`/Users/mohsenrassam/Desktop/Lumenly/docs/runbooks/llm-provider-failure.md`**
    - LLM provider failure runbook

26. **`/Users/mohsenrassam/Desktop/Lumenly/docs/runbooks/security-anomaly.md`**
    - Security anomaly runbook

27. **`/Users/mohsenrassam/Desktop/Lumenly/apps/backend/tests/test_monitoring_alerts.py`**
    - Monitoring and alerting test suite
    - Configuration validation tests
    - Security tests
    - Alert semantics tests
    - Regression tests

### Files to Delete/Replace

28. **`/Users/mohsenrassam/Desktop/Lumenly/apps/backend/monitoring/prometheus-alerts.yml`**
    - Replace with new rule files in `monitoring/prometheus/rules/`

29. **`/Users/mohsenrassam/Desktop/Lumenly/apps/backend/monitoring/grafana-dashboard.json`**
    - Replace with new dashboards in `monitoring/grafana/dashboards/`

---

## IMPLEMENTATION PLAN

### Phase 1: Configuration Fixes (P0)
1. Fix `prometheus.yml` metrics path
2. Update Docker Compose to mount rule files
3. Add Alertmanager service to Docker Compose
4. Add Grafana provisioning to Docker Compose

### Phase 2: Alert Rules (P0/P1)
1. Create backend availability alerts
2. Create dependency failure alerts
3. Create Celery alerts
4. Create security alerts
5. Create LLM alerts
6. Delete outdated `prometheus-alerts.yml`

### Phase 3: Alertmanager (P1)
1. Create Alertmanager configuration
2. Configure routing rules
3. Configure notification channels (environment variables)
4. Test Alertmanager startup

### Phase 4: Grafana Dashboards (P2)
1. Create Prometheus datasource provisioning
2. Create dashboard provisioning
3. Create API overview dashboard
4. Create dependencies dashboard
5. Create Celery dashboard
6. Create AI/LLM dashboard
7. Create security dashboard
8. Delete outdated dashboard

### Phase 5: Runbooks (P2)
1. Create backend down runbook
2. Create high error rate runbook
3. Create high latency runbook
4. Create dependency unavailable runbooks (4)
5. Create Celery failures runbook
6. Create LLM provider failure runbook
7. Create security anomaly runbook

### Phase 6: Test Suite (P2)
1. Create configuration validation tests
2. Create security tests
3. Create alert semantics tests
4. Create regression tests

### Phase 7: Runtime Verification (P0)
1. Start monitoring stack
2. Verify Prometheus scrapes backend
3. Verify metrics appear in Prometheus
4. Verify alert rules load without errors
5. Verify Alertmanager starts
6. Verify Grafana starts with dashboards
7. Generate test traffic
8. Verify alerts fire correctly
9. Verify alerts resolve correctly
10. Verify graceful shutdown

---

## ACCEPTANCE CRITERIA

### Mandatory Gates

- [ ] Prometheus configuration validated (metrics path fixed)
- [ ] Lumenly successfully scraped by Prometheus
- [ ] Alert rules validated (no syntax errors)
- [ ] Backend availability alert verified (P0)
- [ ] High-error alert verified (P1)
- [ ] Latency alert verified (P1/P2)
- [ ] Dependency alerts verified (P0/P1)
- [ ] Celery alerts verified (P1/P2)
- [ ] LLM alerts verified (P1/P2)
- [ ] Security alerts verified (P1/P2)
- [ ] Metrics endpoint remains accessible
- [ ] No sensitive information exposed in alerts
- [ ] Cardinality remains bounded in alerts
- [ ] Existing security tests remain valid
- [ ] Tenant isolation remains intact
- [ ] Celery remains synchronous
- [ ] Prometheus multiprocess support remains functional
- [ ] Recovery behavior verified
- [ ] Graceful shutdown verified

---

## FINAL DECISION

**PROCEED WITH IMPLEMENTATION**

The forensic audit reveals a solid observability foundation with clear gaps in the operational monitoring layer. The existing metrics, logging, and health endpoints are production-ready and require no changes. The implementation should focus on:

1. Fixing Prometheus configuration (metrics path)
2. Creating comprehensive alert rules
3. Adding Alertmanager
4. Provisioning Grafana dashboards
5. Creating operational runbooks
6. Creating monitoring test suite
7. Runtime verification

No unnecessary modifications to the existing observability foundation are required.

---

**Audit Completed By:** Cascade (AI Assistant)  
**Audit Date:** 2026-09-01  
**Audit Version:** 1.0  
**Status:** FORENSIC AUDIT COMPLETE — PROCEED WITH IMPLEMENTATION
