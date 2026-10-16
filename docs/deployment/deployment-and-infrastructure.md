# Deployment and Infrastructure

## Overview

Lumenly's deployment infrastructure is designed for scalability and reliability. The current implementation focuses on local development with Docker Compose. Production deployment configuration is planned but not verified.

## Current Deployment State

### Local Development

**Status:** Implemented and verified

**Components:**
- Docker Compose for service orchestration
- PostgreSQL, MongoDB, Redis, Qdrant services
- FastAPI backend running directly (not containerized in Docker Compose)

**Evidence:**
- Docker Compose configuration in `infra/docker-compose.yml`
- Backend runs directly in test environment

### Production Deployment

**Status:** Not verified

**Planned Components:**
- Kubernetes deployment
- Horizontal scaling of FastAPI workers
- Redis cluster for distributed caching
- MongoDB Atlas sharding
- Qdrant sharding
- Load balancer with TLS termination

**Evidence:**
- No production deployment configuration found
- CI workflow builds Docker images but does not deploy

## Deployment Topology

### Current Topology (Local Development)

```
┌─────────────┐
│   Frontend  │ (Local/Expo)
└──────┬──────┘
       │ HTTP/WebSocket
       ▼
┌─────────────────────────────────────┐
│         FastAPI Backend             │
│  (Running directly, not containerized)│
└──────┬──────────────────────────────┘
       │
    ┌──┼──────────────────────────┐
    ▼  ▼                          ▼
┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐
│  PG   │  │  Mongo│  │ Redis │  │ Qdrant│
│ (Docker)│ (Docker)│ (Docker)│ (Docker)│
└───────┘  └───────┘  └───────┘  └───────┘
```

### Planned Topology (Production)

```
                    ┌─────────────┐
                    │   Load      │
                    │  Balancer   │
                    │  (TLS Term) │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌─────────┐  ┌─────────┐  ┌─────────┐
         │  FastAPI│  │  FastAPI│  │  FastAPI│
         │ Worker 1│  │ Worker 2│  │ Worker N│
         └────┬────┘  └────┬────┘  └────┬────┘
              │            │            │
              └────────────┼────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ┌─────────┐      ┌─────────┐      ┌─────────┐
   │PostgreSQL│      │MongoDB  │      │  Redis  │
   │  Atlas   │      │  Atlas  │      │ Cluster │
   └─────────┘      └─────────┘      └─────────┘
                                          │
                                          ▼
                                   ┌─────────┐
                                   │  Qdrant │
                                   │ Cluster │
                                   └─────────┘
```

## Infrastructure Services

### PostgreSQL

**Current Configuration:**
- Version: 15-alpine (Docker)
- Port: 5433 (mapped from 5432)
- Database: lumenly_test (development), lumenly (production)
- User: lumenly
- Password: Configured via environment variable

**Planned Production Configuration:**
- Managed PostgreSQL (e.g., AWS RDS, Google Cloud SQL)
- Connection pooling
- Automated backups
- High availability (multi-AZ)
- Read replicas for scaling

**Evidence:**
- Docker Compose configuration in `infra/docker-compose.yml`
- No production configuration verified

### MongoDB Atlas

**Current Configuration:**
- Version: 7 (Docker)
- Port: 27017
- Database: lumenly_test (development), lumenly (production)
- No authentication required for local

**Planned Production Configuration:**
- MongoDB Atlas managed service
- Sharding for scalability
- Global clusters for data residency
- Automated backups
- Encryption-at-rest
- Index optimization

**Sharding Strategy:**
- Shard key: hashed(userId)
- Zone sharding for data residency (optional)
- Chunk size: 64 MiB

**Evidence:**
- Docker Compose configuration in `infra/docker-compose.yml`
- Sharding design in system architecture docs

### Redis

**Current Configuration:**
- Version: 7-alpine (Docker)
- Port: 6379
- Database: 1 (for rate limiting)
- No authentication required for local

**Planned Production Configuration:**
- Redis Cluster for high availability
- Redis Sentinel for failover
- AOF persistence
- TLS encryption
- Memory optimization

**Uses:**
- Short-term memory (conversation history)
- Rate limiting (distributed counters)
- Caching (profiles, session data)

**Evidence:**
- Docker Compose configuration in `infra/docker-compose.yml`
- Rate limiting implementation

### Qdrant

**Current Configuration:**
- Version: latest (Docker)
- Port: 6333
- No authentication required for local
- In-memory storage (default)

**Planned Production Configuration:**
- Qdrant Cluster for high availability
- Persistent storage
- Replication
- TLS encryption
- Collection optimization

**Collections:**
- memory_vectors (per-user or user_id filter)
- knowledge_base (user_id filter)

**Evidence:**
- Docker Compose configuration in `infra/docker-compose.yml`
- Vector storage implementation

## Docker Configuration

### Backend Dockerfile

**Location:** `apps/backend/Dockerfile`

**Base Image:** Python 3.11

**Build Process:**
- Copy requirements.txt
- Install dependencies
- Copy application code
- Set working directory
- Expose port 8000
- Run with uvicorn

**Evidence:**
- `apps/backend/Dockerfile`

### Docker Compose

**Location:** `infra/docker-compose.yml`

**Services:**
- postgres: PostgreSQL 15-alpine
- mongodb: MongoDB 7
- redis: Redis 7-alpine
- qdrant: Qdrant latest

**Health Checks:**
- PostgreSQL: pg_isready
- MongoDB: ping command
- Redis: redis-cli ping
- Qdrant: HTTP GET /

**Evidence:**
- `infra/docker-compose.yml`

## CI/CD Pipeline

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

**Test Job:**
- Checkout code
- Set up Python 3.11
- Install dependencies
- Verify service connectivity
- Run tests
- Run tests with coverage

**Lint Job:**
- Checkout code
- Set up Python 3.11
- Install dependencies
- Run Ruff check with auto-fix
- Run Ruff format

**Security Scan Job:**
- Checkout code
- Run TruffleHog (only verified secrets)

**Build Job:**
- Checkout code
- Set up Docker Buildx
- Build Docker image
- Test Docker image

**Evidence:**
- `.github/workflows/ci.yml`

### CD Workflow

**Location:** `.github/workflows/deploy.yml`

**Status:** Not verified

**Planned Deployment:**
- Build Docker image
- Push to container registry
- Deploy to Kubernetes
- Run smoke tests
- Rollback on failure

**Evidence:**
- `.github/workflows/deploy.yml` exists but not verified

## Configuration Management

### Environment Variables

**Required Variables:**
- APP_ENV: development, staging, production, test
- SECRET_KEY: Application secret key (32+ characters)
- JWT_SECRET: JWT signing secret (32+ characters)
- POSTGRES_URL: PostgreSQL connection URL
- MONGODB_URL: MongoDB connection URL
- REDIS_URL: Redis connection URL
- QDRANT_URL: Qdrant service URL

**Optional Variables:**
- GROQ_API_KEY: Groq API key
- GEMINI_API_KEY: Gemini API key
- OPENAI_API_KEY: OpenAI API key
- COHERE_API_KEY: Cohere API key
- ELEVENLABS_API_KEY: ElevenLabs API key
- JWT_SECRET_RS256_PRIVATE: RS256 private key
- JWT_SECRET_RS256_PUBLIC: RS256 public key

**Rate Limiting Variables:**
- RATE_LIMIT_ENABLED: Enable/disable rate limiting
- RATE_LIMIT_FAIL_OPEN: Fail-open on Redis failure
- RATE_LIMIT_TRUSTED_PROXIES: Trusted proxy CIDR ranges

**Evidence:**
- Configuration in `apps/backend/app/core/config.py`
- Example in `apps/backend/.env`

### Configuration Validation

**Production Validation:**
- Rejects placeholder secrets
- Validates secret key length
- Validates environment contracts
- Checks for localhost in production URLs
- Checks for localhost in CORS origins

**Staging Validation:**
- Production-like behavior
- Rate limiting required
- APP_DEBUG must be False

**Development Validation:**
- Flexible configuration
- Warnings for obvious issues

**Evidence:**
- Configuration validation in `apps/backend/app/core/config.py`

## Secrets Handling

### Current State

**Storage:**
- Environment variables
- .env files (not committed to Git)
- CI/CD secrets (GitHub Actions secrets)

**Validation:**
- Rejects known placeholder secrets in production
- Validates secret key length
- Checks for test patterns

**Rotation:**
- No automated rotation
- Manual process required

**Evidence:**
- Configuration validation in `apps/backend/app/core/config.py`
- .env files in `.gitignore`

### Best Practices

**Do Not:**
- Commit secrets to Git
- Use placeholder secrets in production
- Share secrets in plaintext
- Log secrets

**Do:**
- Use environment variables
- Use secret management (e.g., HashiCorp Vault, AWS Secrets Manager)
- Rotate secrets regularly
- Use different secrets per environment

**Evidence:**
- Configuration validation
- TruffleHog secret scanning in CI

## Monitoring and Observability

### Current State

**Metrics:**
- Prometheus metrics exported at `/v1/metrics`
- HTTP request metrics
- Database health metrics
- Rate limiting metrics
- Security metrics
- WebSocket metrics

**Logging:**
- Structured logging with JSON format
- Request correlation via X-Request-ID
- Error logging with full context
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

**Health Checks:**
- `/health/live` - Liveness probe
- `/health/ready` - Readiness probe
- `/health` - Legacy health check

**Evidence:**
- Metrics in `apps/backend/app/core/metrics.py`
- Logging in `apps/backend/app/core/logging_config.py`
- Health checks in `apps/backend/app/main.py`

### Planned Improvements

**Alerting:**
- Prometheus Alertmanager
- PagerDuty integration
- Slack notifications

**Dashboards:**
- Grafana dashboards
- Real-time metrics visualization
- Service health overview

**Distributed Tracing:**
- OpenTelemetry integration
- Jaeger or Zipkin
- End-to-end tracing

**Evidence:**
- No alerting or dashboard configuration found

## Scaling Strategy

### Horizontal Scaling

**FastAPI Workers:**
- Stateless design enables horizontal scaling
- Kubernetes Deployment with replicas
- Auto-scaling based on CPU/RAM
- Load balancer distributes traffic

**Redis Cluster:**
- Distributed caching across workers
- Redis Sentinel for failover
- Redis Cluster for sharding

**MongoDB Atlas:**
- Sharding for scalability
- Read replicas for read scaling
- Global clusters for data residency

**Qdrant Cluster:**
- Sharding for vector storage
- Replication for high availability
- Distributed search

**Evidence:**
- Stateless API design
- Sharding strategy in system architecture docs

### Vertical Scaling

**Resource Limits:**
- CPU limits per pod
- Memory limits per pod
- Database instance sizing
- Redis instance sizing

**Evidence:**
- No resource limits configured in current implementation

## Backup and Recovery

### Current State

**Not Implemented:**
- No automated backups
- No backup schedule
- No recovery procedures documented

**Runbooks:**
- `docs/runbooks/backup-restoration.md` (exists but not verified)
- `docs/runbooks/mongodb-recovery.md`
- `docs/runbooks/postgres-recovery.md`
- `docs/runbooks/redis-recovery.md`
- `docs/runbooks/qdrant-recovery.md`

**Evidence:**
- Runbooks exist but not verified

### Planned Improvements

**Automated Backups:**
- PostgreSQL automated backups (AWS RDS, Google Cloud SQL)
- MongoDB Atlas automated backups
- Redis persistence (AOF/RDB)
- Qdrant snapshots

**Backup Strategy:**
- Daily full backups
- Hourly incremental backups
- Point-in-time recovery
- Cross-region backup replication

**Recovery Procedures:**
- Documented recovery runbooks
- Regular recovery drills
- RTO/RPO targets

**Evidence:**
- Runbooks in `docs/runbooks/`

## Disaster Recovery

### Current State

**Not Implemented:**
- No disaster recovery plan
- No multi-region deployment
- No failover procedures

**Evidence:**
- No disaster recovery documentation found

### Planned Improvements

**Multi-Region Deployment:**
- Multi-region Kubernetes clusters
- Database replication across regions
- DNS-based failover
- Traffic steering

**Failover Strategy:**
- Automatic failover for databases
- Manual failover for application
- Graceful degradation
- Data consistency checks

**Evidence:**
- System architecture mentions multi-region capability

## Known Limitations

1. **No Production Deployment:** Production deployment not verified
2. **No Automated Backups:** No automated backup or recovery
3. **No Disaster Recovery:** No disaster recovery plan
4. **No Monitoring Dashboards:** No Grafana or alerting configured
5. **No Distributed Tracing:** No OpenTelemetry integration
6. **No Secrets Management:** No secret manager integration
7. **No Auto-Scaling:** No Kubernetes auto-scaling configured
8. **No CDN:** No content delivery network for static assets
