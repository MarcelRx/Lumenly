# PostgreSQL Recovery Runbook

## Overview

This runbook covers PostgreSQL recovery procedures for Lumenly, including backup restoration and disaster recovery scenarios.

---

## Symptoms

PostgreSQL may need recovery if:
- Database corruption detected
- Accidental data deletion
- Failed migration requiring rollback
- Complete database loss
- Hardware failure

---

## Detection

### Health Check Failure

```bash
curl http://localhost:8000/health/ready
```

**Expected:** `{"status":"healthy","checks":{"postgres":"healthy",...}}`

**Failure:** `{"status":"unhealthy","checks":{"postgres":"unhealthy",...}}`

### Application Errors

- Database connection errors in logs
- Authentication failures
- Query timeouts
- "relation does not exist" errors

### Monitoring Alerts

- `PostgreSQLUnavailable` (P0) - Database completely unavailable
- `HighHTTPLatencyP95` (P1) - Possible database performance issue
- `DatabaseOperationFailures` (P2) - Increasing database operation failures

---

## Prerequisites

- PostgreSQL backup file available
- Backup verification completed
- PostgreSQL client tools installed (`pg_dump`, `pg_restore`, `psql`)
- Database credentials available
- Sufficient disk space for restore

---

## Recovery Procedures

### Procedure 1: Restore from Backup

**Use when:** Database needs to be restored from a known-good backup

**Steps:**

1. **Verify Backup File**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/backups/postgres
   
   # List available backups
   ls -lh lumenly_postgres_*.dump
   
   # Verify backup integrity
   pg_restore -l lumenly_postgres_<timestamp>.dump
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
   ./restore_postgres.sh lumenly_postgres_<timestamp>.dump
   
   # Or force restore (skip confirmation)
   ./restore_postgres.sh lumenly_postgres_<timestamp>.dump --force
   ```

4. **Verify Restore**
   ```bash
   # Enter PostgreSQL container
   docker compose exec postgres psql -U lumenly -d lumenly
   
   # Check tables exist
   \dt
   
   # Check users table
   SELECT COUNT(*) FROM users;
   
   # Check migration version
   SELECT * FROM alembic_version;
   
   # Exit
   \q
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

### Procedure 2: Point-in-Time Recovery (NOT CURRENTLY SUPPORTED)

**Use when:** Need to recover to a specific point in time

**Current Status:** NOT IMPLEMENTED

**Requirements for Future Implementation:**
- WAL archiving configured
- Continuous archiving enabled
- Recovery target time documented
- Sufficient WAL logs available

**Future Procedure:**
1. Stop PostgreSQL
2. Restore base backup
3. Configure recovery target
4. Replay WAL logs to target
5. Start PostgreSQL
6. Verify data

---

### Procedure 3: Partial Table Recovery

**Use when:** Specific table needs recovery without full restore

**Steps:**

1. **Create Temporary Database**
   ```bash
   docker compose exec postgres psql -U lumenly -d postgres -c "CREATE DATABASE lumenly_temp;"
   ```

2. **Restore to Temporary Database**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/backups
   
   # Modify restore script to use temp database
   POSTGRES_DB=lumenly_temp ./restore_postgres.sh lumenly_postgres_<timestamp>.dump --force
   ```

3. **Export Specific Table**
   ```bash
   docker compose exec postgres pg_dump -U lumenly -d lumenly_temp -t users > users_table.sql
   ```

4. **Import to Production Database**
   ```bash
   docker compose exec postgres psql -U lumenly -d lumenly -f users_table.sql
   ```

5. **Clean Up**
   ```bash
   docker compose exec postgres psql -U lumenly -d postgres -c "DROP DATABASE lumenly_temp;"
   ```

**Warning:** This procedure is risky and should only be used by experienced DBAs

---

### Procedure 4: Emergency Recovery (No Backup Available)

**Use when:** No backup available and database is corrupted

**Steps:**

1. **Assess Damage**
   ```bash
   docker compose exec postgres psql -U lumenly -d lumenly
   
   # Check which tables are accessible
   \dt
   
   # Check table integrity
   SELECT COUNT(*) FROM users;
   SELECT COUNT(*) FROM alembic_version;
   ```

2. **Extract Recoverable Data**
   ```bash
   # Export accessible tables
   docker compose exec postgres pg_dump -U lumenly -d lumenly -t users > users_emergency.sql
   ```

3. **Recreate Database**
   ```bash
   docker compose exec postgres psql -U lumenly -d postgres -c "DROP DATABASE lumenly;"
   docker compose exec postgres psql -U lumenly -d postgres -c "CREATE DATABASE lumenly;"
   ```

4. **Run Migrations**
   ```bash
   docker compose exec backend alembic upgrade head
   ```

5. **Import Recoverable Data**
   ```bash
   docker compose exec postgres psql -U lumenly -d lumenly -f users_emergency.sql
   ```

6. **Verify Data Integrity**
   ```bash
   docker compose exec postgres psql -U lumenly -d lumenly -c "SELECT COUNT(*) FROM users;"
   ```

**Warning:** This procedure may result in data loss. Use only as last resort.

---

## Verification

### Database Level Verification

```bash
# Enter PostgreSQL
docker compose exec postgres psql -U lumenly -d lumenly

# Check all tables exist
\dt

# Check critical tables
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM alembic_version;

# Check indexes
\di

# Exit
\q
```

### Application Level Verification

```bash
# Health check
curl http://localhost:8000/health/ready

# Test authentication
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'
```

### Security Verification

```bash
# Verify authentication still works
# Verify tenant isolation still enforced
# Test cross-tenant access (should be denied)
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
- Authentication broken after restore
- Tenant isolation broken after restore
- Recovery time exceeds RTO (4 hours)

**Escalation Path:**
1. Senior Engineering
2. Database Administrator
3. CTO

---

## Recovery Duration

**Expected Recovery Times:**

- Small database (< 100MB): 2-5 minutes
- Medium database (100MB-1GB): 5-15 minutes
- Large database (> 1GB): 15-60 minutes

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

- `database_health_status{database="postgresql"}` - Database health
- `database_operation_failures_total{database="postgresql"}` - Operation failures
- `http_request_duration_seconds` - Application latency
- `http_requests_total` - Request rate

### Logs to Monitor

```bash
# PostgreSQL logs
docker compose logs -f postgres

# Backend logs
docker compose logs -f backend

# Restore logs
tail -f /Users/mohsenrassam/Desktop/Lumenly/backups/logs/postgres_restore_*.log
```

---

## References

- Backup script: `/Users/mohsenrassam/Desktop/Lumenly/backups/backup_postgres.sh`
- Restore script: `/Users/mohsenrassam/Desktop/Lumenly/backups/restore_postgres.sh`
- Backup directory: `/Users/mohsenrassam/Desktop/Lumenly/backups/postgres/`
- Log directory: `/Users/mohsenrassam/Desktop/Lumenly/backups/logs/`
- Migration documentation: Alembic migration files

---

## Data Classification

**Critical Data in PostgreSQL:**
- `users` table (authentication, RBAC) - CRITICAL
- `alembic_version` table (migration state) - CRITICAL

**Backup Required:** YES
**RPO Target:** 24 hours
**RTO Target:** 4 hours

---

**Runbook Version:** 1.0
**Last Updated:** 2026-09-01
**Maintained By:** SRE Team
