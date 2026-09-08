# Deployment and Rollback Runbook

## Overview

This runbook covers the deployment and rollback procedures for Lumenly in the current manual deployment environment.

---

## Deployment Procedure

### Prerequisites

- Docker Desktop running
- All environment variables configured in `.docker/docker-compose.yml`
- Database migrations ready (if schema changes)
- Backup completed (if schema changes or critical deployment)

### Pre-Deployment Checklist

- [ ] Review changes in this deployment
- [ ] Check if schema changes are included
- [ ] If schema changes: Run pre-deployment backup
- [ ] Verify environment variables are set
- [ ] Review migration scripts (if applicable)
- [ ] Have rollback plan ready

### Deployment Steps

#### 1. Pre-Deployment Backup (Required for Schema Changes)

```bash
# Backup PostgreSQL
cd /Users/mohsenrassam/Desktop/Lumenly/backups
./backup_postgres.sh

# Backup MongoDB
./backup_mongo.sh
```

**Verification:**
- Check backup files exist in `backups/postgres/` and `backups/mongo/`
- Check backup files are non-zero size
- Check logs in `backups/logs/`

#### 2. Stop Current Services

```bash
cd /Users/mohsenrassam/Desktop/Lumenly/.docker
docker compose down
```

#### 3. Build New Images

```bash
docker compose build backend celery-worker
```

#### 4. Start Services

```bash
docker compose up -d
```

#### 5. Run Migrations (If Schema Changes)

```bash
# Enter backend container
docker compose exec backend bash

# Run migrations
alembic upgrade head

# Exit container
exit
```

#### 6. Health Verification

```bash
# Check container status
docker compose ps

# Check health endpoint
curl http://localhost:8000/health/live

# Check readiness endpoint
curl http://localhost:8000/health/ready
```

**Expected Results:**
- All containers show "Up" or "Up (healthy)"
- `/health/live` returns 200
- `/health/ready` returns 200 with all dependencies healthy

#### 7. Smoke Tests

```bash
# Test authentication endpoint
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'

# Test metrics endpoint
curl http://localhost:8000/v1/metrics
```

#### 8. Monitor Logs

```bash
# View backend logs
docker compose logs -f backend

# View celery-worker logs
docker compose logs -f celery-worker
```

**Check For:**
- No startup errors
- Database connections successful
- No authentication errors
- Celery worker connected to Redis

### Deployment Failure

If deployment fails at any step:

1. **Stop the deployment**
2. **Identify the failure point**
3. **Execute rollback procedure** (see below)
4. **Investigate the failure**
5. **Fix the issue**
6. **Retry deployment**

---

## Rollback Procedure

### Prerequisites

- Previous Docker image available (or can be rebuilt)
- Database backup available (if schema changed)
- Rollback plan documented

### Rollback Types

#### Type 1: Application Rollback (No Schema Change)

**Use when:** Application code change failed, but schema unchanged

**Steps:**

1. **Stop Current Services**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/.docker
   docker compose down
   ```

2. **Rebuild Previous Image**
   ```bash
   # Option A: If previous image tag exists
   docker compose pull backend:previous-tag
   docker compose pull celery-worker:previous-tag
   
   # Option B: Rebuild from previous commit
   git checkout <previous-commit-hash>
   docker compose build backend celery-worker
   ```

3. **Start Services**
   ```bash
   docker compose up -d
   ```

4. **Health Verification**
   ```bash
   docker compose ps
   curl http://localhost:8000/health/live
   curl http://localhost:8000/health/ready
   ```

5. **Smoke Tests**
   ```bash
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"test"}'
   ```

#### Type 2: Database Rollback (Schema Change)

**Use when:** Schema migration failed or caused issues

**Steps:**

1. **Stop Current Services**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/.docker
   docker compose down
   ```

2. **Restore Database from Backup**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/backups
   
   # Restore PostgreSQL
   ./restore_postgres.sh <backup_file.dump> --force
   
   # Restore MongoDB (if needed)
   ./restore_mongo.sh <backup_path> --force
   ```

3. **Rebuild Previous Application Image**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/.docker
   git checkout <previous-commit-hash>
   docker compose build backend celery-worker
   ```

4. **Start Services**
   ```bash
   docker compose up -d
   ```

5. **Health Verification**
   ```bash
   docker compose ps
   curl http://localhost:8000/health/live
   curl http://localhost:8000/health/ready
   ```

6. **Verify Data Integrity**
   ```bash
   # Enter backend container
   docker compose exec backend bash
   
   # Check migration version
   alembic current
   
   # Verify users table exists
   psql $POSTGRES_URL -c "SELECT COUNT(*) FROM users;"
   
   # Exit container
   exit
   ```

#### Type 3: Full Rollback (Application + Database)

**Use when:** Both application and database changes are problematic

**Steps:**

1. **Stop Current Services**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/.docker
   docker compose down
   ```

2. **Restore All Databases from Backup**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/backups
   
   ./restore_postgres.sh <backup_file.dump> --force
   ./restore_mongo.sh <backup_path> --force
   ```

3. **Rebuild Previous Application Image**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/.docker
   git checkout <previous-commit-hash>
   docker compose build backend celery-worker
   ```

4. **Start Services**
   ```bash
   docker compose up -d
   ```

5. **Full Health Verification**
   ```bash
   docker compose ps
   curl http://localhost:8000/health/live
   curl http://localhost:8000/health/ready
   ```

6. **Full Smoke Tests**
   ```bash
   # Test authentication
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"test"}'
   
   # Test metrics
   curl http://localhost:8000/v1/metrics
   
   # Test database connectivity
   docker compose exec backend psql $POSTGRES_URL -c "SELECT 1;"
   ```

7. **Verify Tenant Isolation**
   ```bash
   # Attempt cross-tenant access (should be denied)
   curl http://localhost:8000/api/journals \
     -H "Authorization: Bearer <token_for_user_A>" \
     # This should only return user A's journals
   ```

---

## Rollback Verification

### Health Checks

- [ ] All containers running
- [ ] `/health/live` returns 200
- [ ] `/health/ready` returns 200
- [ ] All dependencies healthy in readiness check

### Data Integrity

- [ ] PostgreSQL users table exists
- [ ] MongoDB collections exist
- [ ] Migration version matches expected
- [ ] No data corruption

### Security

- [ ] Authentication still works
- [ ] Tenant isolation still enforced
- [ ] Cross-tenant access denied
- [ ] No secrets exposed in logs

### Functionality

- [ ] API endpoints respond
- [ ] Celery worker connected
- [ ] Metrics endpoint accessible
- [ ] No error spikes in logs

---

## Rollback Duration

**Expected Rollback Times:**

- Application rollback: 2-3 minutes
- Database rollback: 5-10 minutes (depending on data size)
- Full rollback: 10-15 minutes

**Target RTO:** 4 hours (current stage)
**Actual rollback time should be measured and documented**

---

## Common Rollback Scenarios

### Scenario 1: Migration Failed

**Symptoms:**
- Migration script errors
- Database schema inconsistent
- Application fails to start

**Rollback:**
1. Stop services
2. Restore PostgreSQL from backup
3. Rebuild previous application image
4. Start services
5. Verify health

### Scenario 2: Application Crash on Startup

**Symptoms:**
- Container exits immediately
- Application errors in logs
- Health check fails

**Rollback:**
1. Stop services
2. Rebuild previous application image
3. Start services
4. Verify health
5. No database restore needed (schema unchanged)

### Scenario 3: Data Corruption After Deployment

**Symptoms:**
- Application starts but data is inconsistent
- Queries return wrong results
- Tenant isolation broken

**Rollback:**
1. Stop services
2. Restore databases from backup
3. Rebuild previous application image
4. Start services
5. Verify data integrity
6. Verify tenant isolation

### Scenario 4: Performance Degradation

**Symptoms:**
- Application starts but is slow
- High latency
- Timeouts

**Rollback:**
1. Stop services
2. Rebuild previous application image
3. Start services
4. Verify performance
5. No database restore needed (unless schema change)

---

## Escalation

If rollback fails or cannot be completed:

1. **Document the failure**
2. **Preserve all logs**
3. **Preserve failed state for investigation**
4. **Escalate to senior engineering**
5. **Consider emergency procedures** (if available)

---

## Post-Rollback Actions

1. **Document the rollback**
   - What failed
   - Why it failed
   - Rollback duration
   - Verification results

2. **Investigate the failure**
   - Review logs
   - Review code changes
   - Review migration scripts

3. **Fix the issue**
   - Address root cause
   - Add tests to prevent recurrence
   - Update documentation

4. **Schedule retry deployment**
   - After fix is verified
   - During maintenance window if needed
   - With additional monitoring

---

## Monitoring During Rollback

### Metrics to Watch

- `http_requests_total` - Request rate
- `http_request_duration_seconds` - Latency
- `database_health_status` - Database health
- `celery_tasks_total` - Task throughput
- `celery_task_failures_total` - Task failures

### Alerts to Watch

- `BackendDown` - Backend unavailable
- `HighHTTPLatencyP95` - High latency
- `PostgreSQLUnavailable` - PostgreSQL down
- `MongoDBUnavailable` - MongoDB down
- `CeleryWorkerUnavailable` - Celery worker down

---

## References

- Backup procedures: `backup_postgres.sh`, `backup_mongo.sh`
- Restore procedures: `restore_postgres.sh`, `restore_mongo.sh`
- Migration documentation: Alembic migration files
- Health endpoints: `/health/live`, `/health/ready`
- Monitoring: Prometheus, Grafana dashboards

---

**Runbook Version:** 1.0
**Last Updated:** 2026-09-01
**Maintained By:** SRE Team
