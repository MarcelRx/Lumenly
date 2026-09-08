# MongoDB Recovery Runbook

## Overview

This runbook covers MongoDB recovery procedures for Lumenly, including backup restoration and disaster recovery scenarios.

---

## Symptoms

MongoDB may need recovery if:
- Database corruption detected
- Accidental data deletion
- Failed deployment requiring rollback
- Complete database loss
- Hardware failure
- Replica set issues

---

## Detection

### Health Check Failure

```bash
curl http://localhost:8000/health/ready
```

**Expected:** `{"status":"healthy","checks":{"mongo":"healthy",...}}`

**Failure:** `{"status":"unhealthy","checks":{"mongo":"unhealthy",...}}`

### Application Errors

- Database connection errors in logs
- Document query failures
- "connection refused" errors
- Timeout errors

### Monitoring Alerts

- `MongoDBUnavailable` (P0) - Database completely unavailable
- `HighHTTPLatencyP95` (P1) - Possible database performance issue
- `DatabaseOperationFailures` (P2) - Increasing database operation failures

---

## Prerequisites

- MongoDB backup directory available
- Backup verification completed
- MongoDB client tools installed (`mongodump`, `mongorestore`, `mongosh`)
- Database credentials available
- Sufficient disk space for restore

---

## Recovery Procedures

### Procedure 1: Restore from Backup

**Use when:** Database needs to be restored from a known-good backup

**Steps:**

1. **Verify Backup Directory**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/backups/mongo
   
   # List available backups
   ls -lh lumenly_mongo_*
   
   # Verify backup structure
   ls -lh lumenly_mongo_<timestamp>/lumenly/
   ```

2. **Stop Application**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/.docker
   docker compose stop backend celery-worker
   ```

3. **Restore Database**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/backups
   
   # Restore with confirmation prompt
   ./restore_mongo.sh lumenly_mongo_<timestamp>
   
   # Or force restore (skip confirmation)
   ./restore_mongo.sh lumenly_mongo_<timestamp> --force
   ```

4. **Verify Restore**
   ```bash
   # Enter MongoDB container
   docker compose exec mongo mongosh
   
   # Switch to lumenly database
   use lumenly
   
   # Check collections exist
   show collections
   
   # Check document counts
   db.journal_entries.countDocuments()
   db.goals.countDocuments()
   db.habits.countDocuments()
   db.user_documents.countDocuments()
   db.coaching_sessions.countDocuments()
   db.ai_insights.countDocuments()
   db.compliance_events.countDocuments()
   
   # Exit
   exit
   ```

5. **Restart Application**
   ```bash
   docker compose start backend celery-worker
   ```

6. **Health Verification**
   ```bash
   curl http://localhost:8000/health/ready
   ```

**Expected Result:** All checks show "healthy"

---

### Procedure 2: Partial Collection Recovery

**Use when:** Specific collection needs recovery without full restore

**Steps:**

1. **Create Temporary Database**
   ```bash
   docker compose exec mongo mongosh
   use lumenly_temp
   exit
   ```

2. **Restore Specific Collection to Temp Database**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/backups
   
   mongorestore --host localhost \
                --port 27017 \
                --db lumenly_temp \
                --drop \
                lumenly_mongo_<timestamp>/lumenly/journal_entries.bson
   ```

3. **Export Collection**
   ```bash
   docker compose exec mongo mongodump --host localhost \
                                        --port 27017 \
                                        --db lumenly_temp \
                                        --collection journal_entries \
                                        --out /tmp/
   ```

4. **Import to Production Database**
   ```bash
   mongorestore --host localhost \
                --port 27017 \
                --db lumenly \
                --drop \
                /tmp/lumenly_temp/journal_entries.bson
   ```

5. **Clean Up**
   ```bash
   docker compose exec mongo mongosh
   use lumenly_temp
   db.dropDatabase()
   exit
   ```

**Warning:** This procedure is risky and should only be used by experienced DBAs

---

### Procedure 3: Emergency Recovery (No Backup Available)

**Use when:** No backup available and database is corrupted

**Steps:**

1. **Assess Damage**
   ```bash
   docker compose exec mongo mongosh
   use lumenly
   
   # Check which collections are accessible
   show collections
   
   # Check collection integrity
   db.journal_entries.countDocuments()
   db.user_documents.countDocuments()
   ```

2. **Export Recoverable Collections**
   ```bash
   # Export accessible collections
   docker compose exec mongo mongodump --host localhost \
                                        --port 27017 \
                                        --db lumenly \
                                        --collection journal_entries \
                                        --out /tmp/emergency/
   
   docker compose exec mongo mongodump --host localhost \
                                        --port 27017 \
                                        --db lumenly \
                                        --collection user_documents \
                                        --out /tmp/emergency/
   ```

3. **Recreate Database**
   ```bash
   docker compose exec mongo mongosh
   use lumenly
   db.dropDatabase()
   exit
   ```

4. **Recreate Collections**
   ```bash
   # Application will recreate collections on startup
   docker compose restart backend
   ```

5. **Import Recoverable Data**
   ```bash
   mongorestore --host localhost \
                --port 27017 \
                --db lumenly \
                /tmp/emergency/lumenly/journal_entries.bson
   
   mongorestore --host localhost \
                --port 27017 \
                --db lumenly \
                /tmp/emergency/lumenly/user_documents.bson
   ```

6. **Verify Data Integrity**
   ```bash
   docker compose exec mongo mongosh
   use lumenly
   db.journal_entries.countDocuments()
   db.user_documents.countDocuments()
   exit
   ```

**Warning:** This procedure may result in data loss. Use only as last resort.

---

### Procedure 4: Replica Set Recovery (NOT CURRENTLY SUPPORTED)

**Use when:** Replica set member fails

**Current Status:** NOT IMPLEMENTED

**Requirements for Future Implementation:**
- Replica set configured
- Multiple members
- Election mechanism
- Automatic failover

**Future Procedure:**
1. Identify failed member
2. Remove from replica set
3. Rebuild member
4. Add back to replica set
5. Re-sync data
6. Verify replication

---

## Verification

### Database Level Verification

```bash
# Enter MongoDB
docker compose exec mongo mongosh
use lumenly

# Check all collections exist
show collections

# Check critical collections
db.journal_entries.countDocuments()
db.goals.countDocuments()
db.habits.countDocuments()
db.user_documents.countDocuments()
db.coaching_sessions.countDocuments()
db.compliance_events.countDocuments()

# Check indexes
db.journal_entries.getIndexes()
db.user_documents.getIndexes()

# Exit
exit
```

### Application Level Verification

```bash
# Health check
curl http://localhost:8000/health/ready

# Test document retrieval
curl http://localhost:8000/api/journals \
  -H "Authorization: Bearer <token>"
```

### Security Verification

```bash
# Verify tenant isolation still enforced
# Test cross-tenant access (should be denied)
curl http://localhost:8000/api/journals \
  -H "Authorization: Bearer <token_for_user_A>"
# This should only return user A's journals
```

### Data Consistency Verification

```bash
# Verify user_documents have user_id references
docker compose exec mongo mongosh
use lumenly

db.user_documents.find({user_id: {$exists: false}}).count()
# Should return 0

db.user_documents.find({user_id: null}).count()
# Should return 0

exit
```

---

## Rollback/Recovery

If recovery fails:

1. **Stop the recovery**
2. **Preserve current state** (don't delete failed attempt)
3. **Try a different backup** (if available)
4. **Escalate to senior engineering**
5. **Consider emergency recovery procedure**

---

## Escalation

**Escalate if:**
- Multiple backup restore attempts fail
- Data corruption persists after restore
- Tenant isolation broken after restore
- Recovery time exceeds RTO (4 hours)
- Index corruption detected

**Escalation Path:**
1. Senior Engineering
2. Database Administrator
3. CTO

---

## Recovery Duration

**Expected Recovery Times:**

- Small database (< 500MB): 3-8 minutes
- Medium database (500MB-5GB): 8-20 minutes
- Large database (> 5GB): 20-60 minutes

**Target RTO:** 4 hours (current stage)
**Actual recovery time should be measured and documented**

---

## Post-Recovery Actions

1. **Document the recovery**
   - What failed
   - Why it failed
   - Recovery duration
   - Backup used
   - Verification results

2. **Investigate root cause**
   - Review logs
   - Check for hardware issues
   - Check for application errors
   - Check for human error

3. **Prevent recurrence**
   - Add monitoring
   - Add alerts
   - Improve backup frequency
   - Add validation checks

4. **Update documentation**
   - Update runbook with lessons learned
   - Update recovery procedures
   - Update monitoring thresholds

---

## Monitoring During Recovery

### Metrics to Watch

- `database_health_status{database="mongodb"}` - Database health
- `database_operation_failures_total{database="mongodb"}` - Operation failures
- `http_request_duration_seconds` - Application latency
- `http_requests_total` - Request rate

### Logs to Monitor

```bash
# MongoDB logs
docker compose logs -f mongo

# Backend logs
docker compose logs -f backend

# Restore logs
tail -f /Users/mohsenrassam/Desktop/Lumenly/backups/logs/mongo_restore_*.log
```

---

## References

- Backup script: `/Users/mohsenrassam/Desktop/Lumenly/backups/backup_mongo.sh`
- Restore script: `/Users/mohsenrassam/Desktop/Lumenly/backups/restore_mongo.sh`
- Backup directory: `/Users/mohsenrassam/Desktop/Lumenly/backups/mongo/`
- Log directory: `/Users/mohsenrassam/Desktop/Lumenly/backups/logs/`
- Data models: `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/app/models/domain.py`

---

## Data Classification

**Critical Data in MongoDB:**

- `journal_entries` - User journal data - CRITICAL
- `goals` - User goal data - CRITICAL
- `habits` - User habit data - CRITICAL
- `user_documents` - Document source content - CRITICAL (source for vectors)
- `coaching_sessions` - Session history - HIGH
- `compliance_events` - Security/audit events - CRITICAL
- `ai_insights` - AI-generated insights - MEDIUM (regeneratable)

**Backup Required:** YES (except ai_insights)
**RPO Target:** 24 hours
**RTO Target:** 4 hours

---

## Tenant Isolation

All MongoDB collections reference PostgreSQL `user_id`:

- `journal_entries.user_id`
- `goals.user_id`
- `habits.user_id`
- `user_documents.user_id`
- `coaching_sessions.user_id`
- `ai_insights.user_id`
- `compliance_events.user_id`

**Post-Restore Verification Required:**
- All documents have `user_id` field
- No documents with null/missing `user_id`
- Cross-tenant access denied by application layer

---

## Index Verification

After restore, verify critical indexes exist:

```bash
docker compose exec mongo mongosh
use lumenly

# Journal entries indexes
db.journal_entries.getIndexes()

# Goals indexes
db.goals.getIndexes()

# Habits indexes
db.habits.getIndexes()

# User documents indexes
db.user_documents.getIndexes()

# Coaching sessions indexes
db.coaching_sessions.getIndexes()

# AI insights indexes
db.ai_insights.getIndexes()

# Compliance events indexes
db.compliance_events.getIndexes()

exit
```

---

**Runbook Version:** 1.0
**Last Updated:** 2026-09-01
**Maintained By:** SRE Team
