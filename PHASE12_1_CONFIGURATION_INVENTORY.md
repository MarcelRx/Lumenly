# PHASE 12.1 — CONFIGURATION INVENTORY

**Generated:** 2026-09-12  
**Purpose:** Complete inventory of all configuration variables across the Lumenly application  
**Scope:** Phase 12.1 Production Configuration Hardening

---

## CONFIGURATION SOURCES

| Source | Path | Purpose | Environment Scope |
|--------|------|---------|-------------------|
| Docker Compose | `.docker/docker-compose.yml` | Local development orchestration | Development |
| Config Module | `apps/backend/app/core/config.py` | Application configuration & validation | All environments |
| Test Fixture | `apps/backend/tests/conftest.py` | Test environment defaults | Test |
| CI Workflow | `.github/workflows/ci.yml` | CI/CD pipeline configuration | CI/Test |
| Main Application | `apps/backend/app/main.py` | Runtime validation & middleware | All environments |
| Dockerfile | `apps/backend/Dockerfile` | Container build configuration | Production |

---

## CONFIGURATION VARIABLE INVENTORY

### Application Core Configuration

| NAME | SOURCE | DEFAULT | DEVELOPMENT VALUE | TEST VALUE | STAGING VALUE | PRODUCTION REQUIREMENT | SECRET? | FAIL-FAST? |
|------|--------|---------|-------------------|------------|--------------|------------------------|---------|------------|
| APP_ENV | config.py (line 16) | `development` | `development` | `development` | `staging` | `production` (explicit) | NO | YES |
| APP_NAME | config.py (line 17) | `Lumenly` | `Lumenly` | `Lumenly` | `Lumenly` | `Lumenly` | NO | NO |
| VERSION | config.py (line 18) | `0.1.0` | `0.1.0` | `0.1.0` | `0.1.0` | `0.1.0` | NO | NO |
| APP_DEBUG | config.py (line 19) | `True` | `True` | `False` | `False` | `False` (mandatory) | NO | YES |

### Security Secrets

| NAME | SOURCE | DEFAULT | DEVELOPMENT VALUE | TEST VALUE | STAGING VALUE | PRODUCTION REQUIREMENT | SECRET? | FAIL-FAST? |
|------|--------|---------|-------------------|------------|--------------|------------------------|---------|------------|
| SECRET_KEY | docker-compose.yml (line 150) | `3c46e615fffb5d019f5b2b67978607a17f8ac753b5f61b22af4b1c8ecd221cb9d319ae16ec0da5d1efea8d55f8968292c3fbdcdb4067b53df2bc0e9a1298384d` (hardcoded) | External env or hardcoded default | `test-secret-key-for-testing-32bytes-min` | External env | External env (required, min 32 chars) | YES | YES |
| JWT_SECRET | docker-compose.yml (line 160) | `62925d227ba2ba56de1734a39b223d8e7f0e1de5519f25b8e6db70309ce6b2eddc658f364d70b63611e5c542dd43ca65152db3f3b16d7df1da8f2fc877b77e46` (hardcoded) | External env or hardcoded default | `test-jwt-secret-for-testing-32bytes-min` | External env | External env (required, min 32 chars, != SECRET_KEY) | YES | YES |
| JWT_SECRET_RS256_PRIVATE | docker-compose.yml (line 163) | `None` | `None` | `test-rs256-private-key-for-testing-32bytes-min` | External env | External env (if RS256 algorithm used) | YES | YES* |
| JWT_SECRET_RS256_PUBLIC | docker-compose.yml (line 164) | `None` | `None` | `test-rs256-public-key-for-testing-32bytes-min` | External env | External env (if RS256 algorithm used) | YES | YES* |

*Required only if JWT_ALGORITHM=RS256

### Infrastructure URLs

| NAME | SOURCE | DEFAULT | DEVELOPMENT VALUE | TEST VALUE | STAGING VALUE | PRODUCTION REQUIREMENT | SECRET? | FAIL-FAST? |
|------|--------|---------|-------------------|------------|--------------|------------------------|---------|------------|
| POSTGRES_URL | docker-compose.yml (line 151) | `postgresql+asyncpg://lumenly:lumenly_secure_password_32chars@postgres:5432/lumenly` | External env or constructed default | `postgresql+asyncpg://lumenly:lumenly_secure_password_32chars@localhost:5433/lumenly_test` | External env | External env (no localhost) | YES | YES |
| MONGODB_URL | docker-compose.yml (line 152) | `mongodb://mongo:27017/lumenly?replicaSet=rs0` | External env or default | `mongodb://localhost:27017/lumenly_test` | External env | External env (no localhost) | YES | YES |
| REDIS_URL | docker-compose.yml (line 153) | `redis://redis:6379/0` | External env or default | `redis://localhost:6379/1` | External env | External env (no localhost) | YES | YES |
| QDRANT_URL | docker-compose.yml (line 154) | `http://qdrant:6333` | External env or default | `http://localhost:6333` | External env | External env (no localhost) | YES | YES |
| QDRANT_HOST | docker-compose.yml (line 155) | `localhost` | `qdrant` | `localhost` | External host | External host | NO | NO |
| QDRANT_PORT | docker-compose.yml (line 156) | `6333` | `6333` | `6333` | External port | External port | NO | NO |
| QDRANT_API_KEY | config.py (line 139) | `None` | `None` | `None` | External env | External env (if Qdrant cloud) | YES | NO |

### Database Credentials

| NAME | SOURCE | DEFAULT | DEVELOPMENT VALUE | TEST VALUE | STAGING VALUE | PRODUCTION REQUIREMENT | SECRET? | FAIL-FAST? |
|------|--------|---------|-------------------|------------|--------------|------------------------|---------|------------|
| POSTGRES_USER | docker-compose.yml (line 12) | `lumenly` | `lumenly` | `lumenly` | External env | External env | YES | YES |
| POSTGRES_PASSWORD | docker-compose.yml (line 13) | `lumenly_secure_password_32chars` | External env or default | `lumenly_secure_password_32chars` | External env | External env (not placeholder) | YES | YES |
| POSTGRES_DB | docker-compose.yml (line 14) | `lumenly` | `lumenly` | `lumenly_test` | External env | External env | NO | NO |

### LLM Provider Credentials

| NAME | SOURCE | DEFAULT | DEVELOPMENT VALUE | TEST VALUE | STAGING VALUE | PRODUCTION REQUIREMENT | SECRET? | FAIL-FAST? |
|------|--------|---------|-------------------|------------|--------------|------------------------|---------|------------|
| GROQ_API_KEY | docker-compose.yml (line 157) | `None` (blank) | External env | `` (empty string) | External env | External env (at least one LLM key required) | YES | YES* |
| GEMINI_API_KEY | docker-compose.yml (line 158) | `None` (blank) | External env | `` (empty string) | External env | External env (at least one LLM key required) | YES | YES* |
| ELEVENLABS_API_KEY | docker-compose.yml (line 159) | `None` (blank) | External env | `` (empty string) | External env | External env (if voice features used) | YES | NO |
| OPENAI_API_KEY | config.py (line 153) | `None` | External env | `` (empty string) | External env | External env (if OpenAI used) | YES | NO |
| COHERE_API_KEY | config.py (line 154) | `None` | External env | `` (empty string) | External env | External env (if Cohere used) | YES | NO |

*At least one of GROQ_API_KEY or GEMINI_API_KEY must be set in production

### JWT Configuration

| NAME | SOURCE | DEFAULT | DEVELOPMENT VALUE | TEST VALUE | STAGING VALUE | PRODUCTION REQUIREMENT | SECRET? | FAIL-FAST? |
|------|--------|---------|-------------------|------------|--------------|------------------------|---------|------------|
| JWT_ALGORITHM | docker-compose.yml (line 161) | `HS256` | `HS256` | `HS256` | `HS256` or `RS256` | `HS256` or `RS256` | NO | NO |
| ACCESS_TOKEN_EXPIRE_MINUTES | docker-compose.yml (line 162) | `30` | `30` | `15` (config.py default) | External env | External env | NO | NO |
| REFRESH_TOKEN_EXPIRE_DAYS | config.py (line 170) | `7` | `7` | `7` | External env | External env | NO | NO |

### CORS Configuration

| NAME | SOURCE | DEFAULT | DEVELOPMENT VALUE | TEST VALUE | STAGING VALUE | PRODUCTION REQUIREMENT | SECRET? | FAIL-FAST? |
|------|--------|---------|-------------------|------------|--------------|------------------------|---------|------------|
| ALLOW_ORIGINS | docker-compose.yml (line 175) | `http://localhost:3000,http://localhost:8000` | External env or localhost | `*` (test fixture) | External env | External env (no localhost, no wildcard) | NO | YES |
| ALLOW_CREDENTIALS | docker-compose.yml (line 176) | `True` | `True` | `True` | External env | External env | NO | NO |
| ALLOW_METHODS | config.py (line 192) | `GET,POST,PUT,DELETE,OPTIONS,PATCH` | Default | `*` (test fixture) | Default | Default | NO | NO |
| ALLOW_HEADERS | config.py (line 193) | `Content-Type,Authorization,X-Request-ID` | Default | `*` (test fixture) | Default | Default | NO | NO |

### Rate Limiting Configuration

| NAME | SOURCE | DEFAULT | DEVELOPMENT VALUE | TEST VALUE | STAGING VALUE | PRODUCTION REQUIREMENT | SECRET? | FAIL-FAST? |
|------|--------|---------|-------------------|------------|--------------|------------------------|---------|------------|
| RATE_LIMIT_ENABLED | docker-compose.yml (line 169) | `false` (hardcoded) | `false` | `true` (config.py default) | `true` | `true` (mandatory) | NO | YES |
| RATE_LIMIT_REDIS_PREFIX | docker-compose.yml (line 170) | `rate_limit` | `rate_limit` | `rate_limit` | External env | External env | NO | NO |
| RATE_LIMIT_ANONYMOUS_REQUESTS | docker-compose.yml (line 171) | `10` | `10` | `10` | External env | External env | NO | NO |
| RATE_LIMIT_AUTHENTICATED_REQUESTS | docker-compose.yml (line 172) | `100` | `100` | `100` | External env | External env | NO | NO |
| RATE_LIMIT_ADMIN_REQUESTS | docker-compose.yml (line 173) | `1000` | `1000` | `1000` | External env | External env | NO | NO |
| RATE_LIMIT_FAIL_OPEN | docker-compose.yml (line 174) | `false` | `false` | `false` | `false` | `false` (mandatory) | NO | YES |

### Embedding Configuration

| NAME | SOURCE | DEFAULT | DEVELOPMENT VALUE | TEST VALUE | STAGING VALUE | PRODUCTION REQUIREMENT | SECRET? | FAIL-FAST? |
|------|--------|---------|-------------------|------------|--------------|------------------------|---------|------------|
| EMBEDDING_PROVIDER | docker-compose.yml (line 165) | `openai` | `openai` | `openai` | External env | External env | NO | NO |
| EMBEDDING_MODEL | docker-compose.yml (line 166) | `text-embedding-3-small` | `text-embedding-3-small` | `text-embedding-3-small` | External env | External env | NO | NO |
| VECTOR_DIMENSION | docker-compose.yml (line 167) | `1536` | `1536` | `1536` | External env | External env (must match provider) | NO | YES |
| DISTANCE_METRIC | docker-compose.yml (line 168) | `Cosine` | `Cosine` | `Cosine` | External env | External env | NO | YES |

### LLM Model Configuration

| NAME | SOURCE | DEFAULT | DEVELOPMENT VALUE | TEST VALUE | STAGING VALUE | PRODUCTION REQUIREMENT | SECRET? | FAIL-FAST? |
|------|--------|---------|-------------------|------------|--------------|------------------------|---------|------------|
| GEMINI_MODEL | config.py (line 158) | `gemini-2.5-flash` | `gemini-2.5-flash` | `gemini-2.5-flash` | External env | External env | NO | NO |
| GEMINI_API_VERSION | config.py (line 159) | `v1beta` | `v1beta` | `v1beta` | External env | External env | NO | NO |

### Monitoring Configuration

| NAME | SOURCE | DEFAULT | DEVELOPMENT VALUE | TEST VALUE | STAGING VALUE | PRODUCTION REQUIREMENT | SECRET? | FAIL-FAST? |
|------|--------|---------|-------------------|------------|--------------|------------------------|---------|------------|
| PROMETHEUS_MULTIPROC_DIR | docker-compose.yml (line 177) | `/tmp/prometheus_multiproc` | `/tmp/prometheus_multiproc` | N/A | External env | External env | NO | NO |

### Grafana Configuration

| NAME | SOURCE | DEFAULT | DEVELOPMENT VALUE | TEST VALUE | STAGING VALUE | PRODUCTION REQUIREMENT | SECRET? | FAIL-FAST? |
|------|--------|---------|-------------------|------------|--------------|------------------------|---------|------------|
| GRAFANA_ADMIN_USER | docker-compose.yml (line 114) | `admin` | `admin` | N/A | External env | External env | YES | YES |
| GRAFANA_ADMIN_PASSWORD | docker-compose.yml (line 115) | `lumenly` | `lumenly` | N/A | External env | External env (not placeholder) | YES | YES |

---

## CRITICAL FINDINGS

### 1. Hardcoded Secrets in Docker Compose
- **SECRET_KEY**: 128-character hex string hardcoded in docker-compose.yml line 150
- **JWT_SECRET**: 128-character hex string hardcoded in docker-compose.yml line 160
- **Risk**: These values are not in the `_PLACEHOLDER_SECRETS` list in config.py
- **Impact**: Production could silently use these development defaults

### 2. Rate Limiting Disabled by Default
- **RATE_LIMIT_ENABLED**: Hardcoded to `false` in docker-compose.yml line 169
- **Config.py default**: `true` (line 240)
- **Conflict**: Docker Compose overrides the safer config.py default
- **Impact**: Production deployments inherit disabled rate limiting

### 3. Development CORS Defaults
- **ALLOW_ORIGINS**: Defaults to `http://localhost:3000,http://localhost:8000`
- **Impact**: Production could inherit localhost-only CORS
- **Validation**: main.py has production wildcard rejection but not localhost rejection

### 4. Database Password Placeholder
- **POSTGRES_PASSWORD**: Default `lumenly_secure_password_32chars`
- **Status**: IS in `_PLACEHOLDER_SECRETS` list (config.py line 32)
- **Impact**: Production startup would fail with current validation
- **Risk**: Development convenience vs production safety

### 5. Blank LLM API Keys
- **GROQ_API_KEY, GEMINI_API_KEY, ELEVENLABS_API_KEY**: Default to blank/None
- **Production requirement**: At least one LLM key required (main.py line 150)
- **Impact**: Production would fail without explicit configuration

### 6. Optional RS256 Keys
- **JWT_SECRET_RS256_PRIVATE, JWT_SECRET_RS256_PUBLIC**: Default to None
- **Current algorithm**: HS256 (docker-compose.yml line 161)
- **Impact**: RS256 not enforced even if algorithm changed

### 7. Debug Mode Enabled
- **APP_DEBUG**: Defaults to `true` in config.py line 19
- **Impact**: Production could inherit debug mode
- **Validation**: main.py does not enforce APP_DEBUG=false in production

### 8. Environment Defaults
- **APP_ENV**: Defaults to `development` in config.py line 16
- **Impact**: Production requires explicit APP_ENV=production
- **Risk**: Silent fallback to development if not set

---

## ENVIRONMENT CONTRACT SUMMARY

### Development
- May use: debug mode, localhost CORS, local services, convenience defaults
- Secrets: Should use development-specific values, not production-like placeholders
- Rate limiting: Can be disabled for convenience
- Database: Can use default credentials

### Test
- Must be: deterministic, isolated, non-dependent on external services
- Secrets: Use explicit test values (32-char minimum)
- CORS: Uses wildcard for test fixtures
- Rate limiting: Uses config.py default (true)
- Database: Uses test database and credentials

### Staging
- Must behave like production for: auth, rate limiting, CORS, secret validation
- Environment: Explicit APP_ENV=staging
- CORS: Should use staging-specific domains
- All production validations should apply

### Production
- Must require:
  - APP_ENV=production (explicit)
  - APP_DEBUG=false (mandatory)
  - RATE_LIMIT_ENABLED=true (mandatory)
  - External SECRET_KEY (min 32 chars, != JWT_SECRET)
  - External JWT_SECRET (min 32 chars)
  - External database credentials (no localhost, no placeholders)
  - External LLM credentials (at least one provider)
  - Production-specific ALLOW_ORIGINS (no localhost, no wildcard)
  - RATE_LIMIT_FAIL_OPEN=false (mandatory)
- Must reject:
  - Placeholder secrets
  - Test secrets
  - Development defaults
  - Localhost in infrastructure URLs
  - Wildcard CORS origins
  - Missing required credentials

---

## VALIDATION MECHANISMS

### Current Validation (config.py)
- `_PLACEHOLDER_SECRETS` list (lines 26-37)
- `_is_placeholder_secret()` method (lines 39-54)
- `_validate_production_secrets()` method (lines 56-112)
- Only runs when APP_ENV=production
- Checks: SECRET_KEY, JWT_SECRET, LLM keys, database passwords

### Current Validation (main.py)
- CORS wildcard rejection in production (lines 80-84)
- CORS wildcard warning in staging (lines 87-94)
- Embedding configuration validation (lines 101-109)
- Production secret length validation (lines 114-124)
- SECRET_KEY != JWT_SECRET check (line 126-127)
- RATE_LIMIT_FAIL_OPEN enforcement (lines 129-134)
- Localhost rejection in infrastructure URLs (lines 137-147)
- LLM API key requirement (lines 150-167)
- Placeholder API key rejection (lines 156-167)
- Calls `_validate_production_secrets()` (line 170)

### Missing Validation
- APP_DEBUG=false not enforced in production
- RATE_LIMIT_ENABLED=true not enforced in production
- Localhost CORS not rejected in production
- RS256 key requirement not enforced when algorithm=RS256
- Grafana credentials not validated

---

## NEXT STEPS

Based on this inventory, Phase 12.1 must address:

1. **Remove hardcoded secrets from Docker Compose** (SECRET_KEY, JWT_SECRET)
2. **Fix RATE_LIMIT_ENABLED default** (currently false in Compose, should be environment-specific)
3. **Enforce APP_DEBUG=false in production**
4. **Enforce RATE_LIMIT_ENABLED=true in production**
5. **Add localhost CORS rejection in production**
6. **Add RS256 key validation when algorithm=RS256**
7. **Ensure production fail-fast for all required credentials**
8. **Add comprehensive configuration tests**
9. **Document environment separation clearly**
10. **Verify no regression to 745-test baseline**

---

**END OF INVENTORY**
