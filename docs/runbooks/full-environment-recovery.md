# Full Environment Recovery Runbook

## Overview

This runbook covers complete environment recovery procedures for Lumenly. This is the disaster recovery scenario where the entire application environment is lost and must be recreated from scratch.

---

## Scenario

**Complete Environment Loss**

This scenario simulates:
- All Docker containers stopped
- All Docker volumes deleted
- Infrastructure completely lost
- Need to recreate everything from backups

---

## Prerequisites

- PostgreSQL backup file available
- MongoDB backup directory available
- Docker installed and running
- Docker Compose installed
- Repository code available
- Environment variables documented
- Backup verification completed

---

## Recovery Procedure

### Step 1: Infrastructure Recreation

1. **Verify Docker is Running**
   ```bash
   docker info
   ```

2. **Navigate to Docker Compose Directory**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/.docker
   ```

3. **Verify Docker Compose Configuration**
   ```bash
   cat docker-compose.yml
   ```

4. **Start Infrastructure Services**
   ```bash
   docker compose up -d postgres mongo redis qdrant
   ```

5. **Verify Services are Running**
   ```bash
   docker compose ps
   ```

6. **Wait for Services to be Healthy**
   ```bash
   # Wait for PostgreSQL to be ready
   docker compose logs -f postgres
   # Wait until "database system is ready to accept connections"
   
   # Wait for MongoDB to be ready
   docker compose logs -f mongo
   # Wait until "waiting for connections"
   
   # Wait for Redis to be ready
   docker compose logs -f redis
   # Wait until "Ready to accept connections"
   
   # Wait for Qdrant to be ready
   docker compose logs -f qdrant
   # Wait until "Acting as leader"
   ```

---

### Step 2: Database Restoration

1. **Restore PostgreSQL**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/backups
   
   # List available backups
   ls -lh postgres/
   
   # Restore latest backup
   ./restore_postgres.sh postgres/lumenly_postgres_<timestamp>.dump --force
   ```

2. **Verify PostgreSQL Restore**
   ```bash
   docker compose exec postgres psql -U lumenly -d lumenly
   
   # Check tables exist
   \dt
   
   # Check users table
   SELECT COUNT(*) FROM users;
   
   # Check migration version
   SELECT * FROM alembic_version;
   
   exit
   ```

3. **Restore MongoDB**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/backups
   
   # List available backups
   ls -lh mongo/
   
   # Restore latest backup
   ./restore_mongo.sh mongo/lumenly_mongo_<timestamp> --force
   ```

4. **Verify MongoDB Restore**
   ```bash
   docker compose exec mongo mongosh
   use lumenly
   
   # Check collections exist
   show collections
   
   # Check document counts
   db.journal_entries.countDocuments()
   db.goals.countDocuments()
   db.habits.countDocuments()
   db.user_documents.countDocuments()
   db.compliance_events.countDocuments()
   
   exit
   ```

---

### Step 3: Application Deployment

1. **Build Application Image**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/.docker
   docker compose build backend celery-worker
   ```

2. **Start Application Services**
   ```bash
   docker compose up -d backend celery-worker
   ```

3. **Verify Services are Running**
   ```bash
   docker compose ps
   ```

4. **Run Migrations** (if needed)
   ```bash
   docker compose exec backend alembic upgrade head
   ```

5. **Verify Migration Version**
   ```bash
   docker compose exec backend alembic current
   ```

---

### Step 4: Monitoring Stack Recovery

1. **Start Monitoring Services**
   ```bash
   docker compose up -d prometheus alertmanager grafana
   ```

2. **Verify Monitoring Services**
   ```bash
   docker compose ps
   ```

3. **Verify Prometheus**
   ```bash
   curl http://localhost:9090/-/healthy
   ```

4. **Verify Grafana**
   ```bash
   curl http://localhost:3000/api/health
   ```

---

### Step 5: Health Verification

1. **Check Application Health**
   ```bash
   curl http://localhost:8000/health/live
   curl http://localhost:8000/health/ready
   ```

2. **Verify All Dependencies Healthy**
   ```bash
   curl http://localhost:8000/health/ready | jq
   ```

3. **Test Authentication**
   ```bash
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"test"}'
   ```

4. **Test Metrics Endpoint**
   ```bash
   curl http://localhost:8000/v1/metrics
   ```

---

### Step 6: Data Integrity Verification

1. **Verify PostgreSQL Data**
   ```bash
   docker compose exec postgres psql -U lumenly -d lumenly
   
   # Check users exist
   SELECT COUNT(*) FROM users;
   
   # Check migration version
   SELECT * FROM alembic_version;
   
   exit
   ```

2. **Verify MongoDB Data**
   ```bash
   docker compose exec mongo mongosh
   use lumenly
   
   # Check collections
   show collections
   
   # Check document counts
   db.journal_entries.countDocuments()
   db.user_documents.countDocuments()
   
   # Verify tenant isolation
   db.user_documents.find({user_id: {$exists: false}}).count()
   # Should return 0
   
   exit
   ```

3. **Verify Qdrant** (if vectors exist)
   ```bash
   # Check Qdrant collections
   curl http://localhost:6333/collections
   ```

---

### Step 7: Security Verification

1. **Verify Authentication Works**
   ```bash
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"test"}'
   ```

2. **Verify Tenant Isolation**
   ```bash
   # Attempt cross-tenant access (should be denied)
   curl http://localhost:8000/api/journals \
     -H "Authorization: Bearer <token_for_user_A>"
   # Should only return user A's journals
   ```

3. **Verify No Secrets Exposed**
   ```bash
   # Check logs for secrets
   docker compose logs backend | grep -i "password\|secret\|key"
   # Should not show actual secrets
   ```

---

### Step 8: Functional Verification

1. **Test Document Upload** (if applicable)
   ```bash
   curl -X POST http://localhost:8000/api/documents \
     -H "Authorization: Bearer <token>" \
     -F "file=@test.txt"
   ```

2. **Test Vector Search** (if applicable)
   ```bash
   curl -X POST http://localhost:8000/api/search \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"query":"test query"}'
   ```

3. **Test Coaching** (if applicable)
   ```bash
   curl -X POST http://localhost:8000/api/coaching/session \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"type":"assessment"}'
   ```

---

### Step 9: Monitoring Verification

1. **Verify Prometheus Metrics**
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

2. **Verify Grafana Dashboards**
   ```bash
   curl http://localhost:3000/api/search
   ```

3. **Verify Alerts**
   ```bash
   curl http://localhost:9093/api/v1/alerts
   ```

---

## Recovery Duration Measurement

**Record the following:**

- Recovery start time: `_______`
- Infrastructure recreation complete: `_______`
- Database restoration complete: `_______`
- Application deployment complete: `_______`
- Monitoring recovery complete: `_______`
- Health verification complete: `_______`
- Recovery end time: `_______`

**Total Recovery Time:** `_______`

**Target RTO:** 4 hours
**Actual RTO:** `_______`

---

## Data Loss Measurement

**Record the following:**

- PostgreSQL backup timestamp: `_______`
- MongoDB backup timestamp: `_______`
- Recovery start time: `_______`

**Maximum Data Loss:** `_______`

**Target RPO:** 24 hours
**Actual RPO:** `_______`

---

## Rollback/Recovery

If recovery fails at any step:

1. **Stop the recovery**
2. **Preserve current state** (don't delete partial recovery)
3. **Identify the failure point**
4. **Try a different backup** (if available)
5. **Escalate to senior engineering**

---

## Escalation

**Escalate if:**
- Infrastructure cannot be recreated
- Database restore fails
- Application cannot start
- Authentication broken
- Tenant isolation broken
- Recovery time exceeds RTO (4 hours)
- Data loss exceeds RPO (24 hours)

**Escalation Path:**
1. Senior Engineering
2. CTO
3. Executive Team

---

## Post-Recovery Actions

1. **Document the recovery**
   - What failed
   - Why it failed
   - Recovery duration
   - Actual RTO
   - Actual RPO
   - Backups used
   - Verification results

2. **Investigate root cause**
   - Review logs
   - Check for hardware issues
   - Check for human error
   - Check for security breach

3. **Prevent recurrence**
   - Add monitoring
   - Add alerts
   - Improve backup frequency
   - Add redundancy
   - Add geographic distribution

4. **Update documentation**
   - Update runbook with lessons learned
   - Update recovery procedures
   - Update RTO/RPO targets if needed

---

## Monitoring During Recovery

### Metrics to Watch

- `http_requests_total` - Request rate
- `http_request_duration_seconds` - Latency
- `database_health_status` - Database health
- `celery_tasks_total` - Task throughput

### Logs to Monitor

```bash
# PostgreSQL logs
docker compose logs -f postgres

# MongoDB logs
docker compose logs -f mongo

# Redis logs
docker compose logs -f redis

# Qdrant logs
docker compose logs -f qdrant

# Backend logs
docker compose logs -f backend

# Celery worker logs
docker compose logs -f celery-worker
```

---

## References

- Backup scripts: `/Users/mohsenrassam/Desktop/Lumenly/backups/`
- Restore scripts: `/Users/mohsenrassam/Desktop/Lumenly/backups/`
- Docker Compose: `/Users/mohsenrassam/Desktop/Lumenly/.docker/docker-compose.yml`
- Recovery runbooks: `/Users/mohsenrassam/Desktop/Lumenly/docs/runbooks/`

---

## Recovery Checklist

- [ ] Docker running
- [ ] Infrastructure services started
- [ ] PostgreSQL restored
- [ ] MongoDB restored
- [ ] Application deployed
- [ ] Migrations run
- [ ] Monitoring started
- [ ] Health checks passing
- [ ] Authentication working
- [ ] Tenant isolation verified
- [ ] Data integrity verified
- [ ] Security verified
- [ ] Functional tests passing
- [ ] Monitoring verified
- [ ] Recovery duration recorded
- [ ] Data loss recorded
- [ ] Documentation updated

---

**Runbook Version:** 1.0
**Last Updated:** 2026-09-01
**Maintained By:** SRE Team
