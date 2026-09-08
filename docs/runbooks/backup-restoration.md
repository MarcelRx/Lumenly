# Backup Restoration Runbook

## Overview

This runbook covers the complete backup restoration procedure for Lumenly. This is used when restoring from a known-good backup point.

---

## Prerequisites

- PostgreSQL backup file available
- MongoDB backup directory available
- Backup verification completed
- Docker running
- Database credentials available
- Sufficient disk space for restore

---

## Restoration Procedure

### Step 1: Backup Selection

1. **List Available Backups**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/backups
   
   # PostgreSQL backups
   ls -lh postgres/
   
   # MongoDB backups
   ls -lh mongo/
   ```

2. **Select Backup Point**
   - Choose backup timestamp
   - Verify backup age is acceptable (within RPO target)
   - Verify backup integrity

3. **Verify Backup Integrity**
   ```bash
   # PostgreSQL
   pg_restore -l postgres/lumenly_postgres_<timestamp>.dump
   
   # MongoDB
   ls -lh mongo/lumenly_mongo_<timestamp>/lumenly/
   ```

---

### Step 2: Pre-Restoration Preparation

1. **Stop Application Services**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/.docker
   docker compose stop backend celery-worker
   ```

2. **Verify Database Services Running**
   ```bash
   docker compose ps postgres mongo
   ```

3. **Create Pre-Restoration Snapshot** (Optional)
   ```bash
   # Backup current state before restore
   cd /Users/mohsenrassam/Desktop/Lumenly/backups
   ./backup_postgres.sh
   ./backup_mongo.sh
   ```

---

### Step 3: PostgreSQL Restoration

1. **Restore PostgreSQL**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/backups
   
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

3. **Verify Restore Duration**
   - Record restore start time
   - Record restore end time
   - Calculate total duration

---

### Step 4: MongoDB Restoration

1. **Restore MongoDB**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/backups
   
   ./restore_mongo.sh mongo/lumenly_mongo_<timestamp> --force
   ```

2. **Verify MongoDB Restore**
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
   db.coaching_sessions.countDocuments()
   db.compliance_events.countDocuments()
   
   # Verify tenant isolation
   db.user_documents.find({user_id: {$exists: false}}).count()
   # Should return 0
   
   exit
   ```

3. **Verify Restore Duration**
   - Record restore start time
   - Record restore end time
   - Calculate total duration

---

### Step 5: Application Restart

1. **Start Application Services**
   ```bash
   docker compose start backend celery-worker
   ```

2. **Verify Services Running**
   ```bash
   docker compose ps
   ```

3. **Run Migrations** (if backup is older than current code)
   ```bash
   docker compose exec backend alembic upgrade head
   ```

4. **Verify Migration Version**
   ```bash
   docker compose exec backend alembic current
   ```

---

### Step 6: Health Verification

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

---

### Step 7: Data Integrity Verification

1. **Verify PostgreSQL Data**
   ```bash
   docker compose exec postgres psql -U lumenly -d lumenly
   
   # Check users exist
   SELECT COUNT(*) FROM users;
   
   # Check specific user data
   SELECT id, email, role FROM users LIMIT 5;
   
   exit
   ```

2. **Verify MongoDB Data**
   ```bash
   docker compose exec mongo mongosh
   use lumenly
   
   # Check document counts match backup
   db.journal_entries.countDocuments()
   db.user_documents.countDocuments()
   
   # Check specific documents
   db.journal_entries.findOne()
   
   exit
   ```

3. **Verify Data Consistency**
   - PostgreSQL user IDs match MongoDB user_id references
   - No orphaned documents
   - No missing references

---

### Step 8: Security Verification

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
   # Check restore logs for secrets
   cat /Users/mohsenrassam/Desktop/Lumenly/backups/logs/postgres_restore_*.log | grep -i "password\|secret"
   # Should not show actual secrets
   ```

---

### Step 9: Functional Verification

1. **Test Document Retrieval**
   ```bash
   curl http://localhost:8000/api/journals \
     -H "Authorization: Bearer <token>"
   ```

2. **Test Goal Retrieval**
   ```bash
   curl http://localhost:8000/api/goals \
     -H "Authorization: Bearer <token>"
   ```

3. **Test Habit Retrieval**
   ```bash
   curl http://localhost:8000/api/habits \
     -H "Authorization: Bearer <token>"
   ```

---

### Step 10: Monitoring Verification

1. **Verify Prometheus Metrics**
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

2. **Verify Application Metrics**
   ```bash
   curl http://localhost:8000/v1/metrics
   ```

3. **Check for Errors**
   ```bash
   docker compose logs backend | grep -i error
   docker compose logs celery-worker | grep -i error
   ```

---

## Rollback/Recovery

If restoration fails:

1. **Stop the restoration**
2. **Preserve current state** (don't delete partial restore)
3. **Try a different backup** (if available)
4. **Restore from pre-restoration snapshot** (if created)
5. **Escalate to senior engineering**

---

## Escalation

**Escalate if:**
- PostgreSQL restore fails
- MongoDB restore fails
- Data integrity verification fails
- Authentication broken after restore
- Tenant isolation broken after restore
- Restore time exceeds RTO (4 hours)

**Escalation Path:**
1. Senior Engineering
2. Database Administrator
3. CTO

---

## Restoration Duration

**Expected Restoration Times:**

- PostgreSQL restore (small): 2-5 minutes
- PostgreSQL restore (medium): 5-15 minutes
- PostgreSQL restore (large): 15-60 minutes
- MongoDB restore (small): 3-8 minutes
- MongoDB restore (medium): 8-20 minutes
- MongoDB restore (large): 20-60 minutes
- Total restoration: 10-120 minutes

**Target RTO:** 4 hours (current stage)
**Actual restoration time should be measured and documented**

---

## Post-Restoration Actions

1. **Document the restoration**
   - Backup timestamp used
   - Restoration duration
   - Verification results
   - Any issues encountered

2. **Investigate root cause** (if restoration was due to failure)
   - Review logs
   - Check for data corruption
   - Check for human error

3. **Prevent recurrence**
   - Add monitoring
   - Add alerts
   - Improve backup frequency
   - Add validation checks

4. **Update documentation**
   - Update runbook with lessons learned
   - Update restoration procedures

---

## Monitoring During Restoration

### Metrics to Watch

- `database_health_status` - Database health
- `http_request_duration_seconds` - Application latency
- `database_operation_failures_total` - Operation failures

### Logs to Monitor

```bash
# PostgreSQL logs
docker compose logs -f postgres

# MongoDB logs
docker compose logs -f mongo

# Backend logs
docker compose logs -f backend

# Restore logs
tail -f /Users/mohsenrassam/Desktop/Lumenly/backups/logs/postgres_restore_*.log
tail -f /Users/mohsenrassam/Desktop/Lumenly/backups/logs/mongo_restore_*.log
```

---

## References

- Backup scripts: `/Users/mohsenrassam/Desktop/Lumenly/backups/backup_*.sh`
- Restore scripts: `/Users/mohsenrassam/Desktop/Lumenly/backups/restore_*.sh`
- Backup directory: `/Users/mohsenrassam/Desktop/Lumenly/backups/`
- Log directory: `/Users/mohsenrassam/Desktop/Lumenly/backups/logs/`

---

## Restoration Checklist

- [ ] Backup selected
- [ ] Backup integrity verified
- [ ] Application services stopped
- [ ] Pre-restoration snapshot created (optional)
- [ ] PostgreSQL restored
- [ ] PostgreSQL restore verified
- [ ] MongoDB restored
- [ ] MongoDB restore verified
- [ ] Application services started
- [ ] Migrations run (if needed)
- [ ] Health checks passing
- [ ] Authentication working
- [ ] Tenant isolation verified
- [ ] Data integrity verified
- [ ] Security verified
- [ ] Functional tests passing
- [ ] Monitoring verified
- [ ] Restoration duration recorded
- [ ] Documentation updated

---

**Runbook Version:** 1.0
**Last Updated:** 2026-09-01
**Maintained By:** SRE Team
