# Database Migration Failure Runbook

## Overview

This runbook covers database migration failure recovery procedures for Lumenly. Alembic is used for PostgreSQL schema migrations.

---

## Symptoms

Migration may fail if:
- Migration script has syntax error
- Migration script has logic error
- Database state inconsistent
- Migration conflicts with existing data
- Migration timeout
- Insufficient database permissions

---

## Detection

### Migration Failure During Deployment

```bash
# Migration command fails
docker compose exec backend alembic upgrade head
# Error message displayed
```

### Application Errors

- Application fails to start after migration
- "relation does not exist" errors
- "column does not exist" errors
- Constraint violation errors

### Monitoring Alerts

- `MigrationFailure` (P0) - Migration failed
- `ApplicationStartupFailure` (P0) - Application cannot start

---

## Prerequisites

- Database backup available (pre-migration)
- Migration script available
- Alembic configuration available
- Database credentials available

---

## Recovery Procedures

### Procedure 1: Migration Rollback (Downgrade)

**Use when:** Migration failed but database is still accessible

**Steps:**

1. **Check Current Migration Version**
   ```bash
   docker compose exec backend alembic current
   ```

2. **Identify Failed Migration**
   ```bash
   docker compose exec backend alembic history
   ```

3. **Rollback to Previous Version**
   ```bash
   # Rollback one step
   docker compose exec backend alembic downgrade -1
   
   # Or rollback to specific version
   docker compose exec backend alembic downgrade <revision_id>
   ```

4. **Verify Rollback**
   ```bash
   docker compose exec backend alembic current
   ```

5. **Verify Database State**
   ```bash
   docker compose exec postgres psql -U lumenly -d lumenly
   
   # Check schema
   \dt
   
   # Check specific tables
   \d users
   
   exit
   ```

6. **Restart Application**
   ```bash
   docker compose restart backend celery-worker
   ```

7. **Verify Application Health**
   ```bash
   curl http://localhost:8000/health/ready
   ```

---

### Procedure 2: Database Restore (Migration Failed with Data Corruption)

**Use when:** Migration corrupted database or rollback not possible

**Steps:**

1. **Stop Application**
   ```bash
   docker compose stop backend celery-worker
   ```

2. **Restore Database from Pre-Migration Backup**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/backups
   
   ./restore_postgres.sh postgres/lumenly_postgres_<pre_migration_timestamp>.dump --force
   ```

3. **Verify Restore**
   ```bash
   docker compose exec postgres psql -U lumenly -d lumenly
   
   # Check migration version
   SELECT * FROM alembic_version;
   
   # Check tables
   \dt
   
   exit
   ```

4. **Investigate Migration Failure**
   - Review migration script
   - Review migration logs
   - Identify root cause

5. **Fix Migration Script**
   - Correct syntax errors
   - Correct logic errors
   - Add data migration if needed

6. **Retry Migration**
   ```bash
   docker compose start backend celery-worker
   docker compose exec backend alembic upgrade head
   ```

---

### Procedure 3: Manual Schema Fix (Migration Cannot Be Reversed)

**Use when:** Migration is irreversible and must be manually fixed

**Steps:**

1. **Assess Damage**
   ```bash
   docker compose exec postgres psql -U lumenly -d lumenly
   
   # Check schema
   \dt
   
   # Check specific table
   \d <problem_table>
   
   # Check data
   SELECT * FROM <problem_table> LIMIT 10;
   
   exit
   ```

2. **Create Manual Fix Script**
   ```bash
   # Create SQL fix script
   cat > /tmp/migration_fix.sql << EOF
   -- Manual fix for migration failure
   BEGIN;
   
   -- Fix schema
   ALTER TABLE <problem_table> ...;
   
   -- Fix data
   UPDATE <problem_table> SET ...;
   
   COMMIT;
   EOF
   ```

3. **Apply Manual Fix**
   ```bash
   docker compose exec -T postgres psql -U lumenly -d lumenly < /tmp/migration_fix.sql
   ```

4. **Update Alembic Version**
   ```bash
   docker compose exec postgres psql -U lumenly -d lumenly
   
   -- Manually update alembic_version to target revision
   UPDATE alembic_version SET version_num = '<target_revision>';
   
   exit
   ```

5. **Verify Fix**
   ```bash
   docker compose exec postgres psql -U lumenly -d lumenly
   
   # Check schema
   \dt
   
   # Check migration version
   SELECT * FROM alembic_version;
   
   exit
   ```

6. **Restart Application**
   ```bash
   docker compose restart backend celery-worker
   ```

7. **Verify Application Health**
   ```bash
   curl http://localhost:8000/health/ready
   ```

**Warning:** Manual schema fixes are risky and should only be performed by experienced DBAs

---

### Procedure 4: Forward-Only Recovery (Downgrade Not Supported)

**Use when:** Migration cannot be downgraded (data loss on downgrade)

**Steps:**

1. **Document the Constraint**
   - Migration is forward-only
   - Downgrade would cause data loss
   - Recovery requires forward migration fix

2. **Fix Migration Script**
   - Correct the migration script
   - Ensure idempotency (can run multiple times)
   - Add data migration if needed

3. **Create New Migration**
   ```bash
   docker compose exec backend alembic revision -m "fix_migration_failure"
   ```

4. **Edit New Migration**
   - Add fix logic
   - Ensure it can be applied on top of failed state
   - Add rollback if possible

5. **Apply New Migration**
   ```bash
   docker compose exec backend alembic upgrade head
   ```

6. **Verify Fix**
   ```bash
   docker compose exec backend alembic current
   curl http://localhost:8000/health/ready
   ```

---

## Migration Safety Testing

### Pre-Deployment Migration Testing

**Test on Staging Environment:**

1. **Create Test Database**
   ```bash
   # Create test database
   docker compose exec postgres psql -U lumenly -d postgres -c "CREATE DATABASE lumenly_test;"
   ```

2. **Restore Backup to Test Database**
   ```bash
   # Modify restore script to use test database
   POSTGRES_DB=lumenly_test ./restore_postgres.sh <backup_file> --force
   ```

3. **Test Migration on Test Database**
   ```bash
   # Update environment to use test database
   # Run migration
   docker compose exec backend alembic upgrade head
   ```

4. **Verify Migration**
   ```bash
   # Check schema
   # Check data
   # Test application
   ```

5. **Test Downgrade** (if safe)
   ```bash
   docker compose exec backend alembic downgrade -1
   ```

6. **Test Upgrade Again**
   ```bash
   docker compose exec backend alembic upgrade head
   ```

---

## Verification

### Migration Level Verification

```bash
# Check current migration version
docker compose exec backend alembic current

# Check migration history
docker compose exec backend alembic history

# Check pending migrations
docker compose exec backend alembic heads
```

### Database Level Verification

```bash
docker compose exec postgres psql -U lumenly -d lumenly

# Check tables
\dt

# Check specific table
\d users

# Check constraints
SELECT conname, contype FROM pg_constraint WHERE conrelid = 'users'::regclass;

# Check indexes
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'users';

exit
```

### Application Level Verification

```bash
# Health check
curl http://localhost:8000/health/ready

# Test authentication
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'

# Test data access
curl http://localhost:8000/api/journals \
  -H "Authorization: Bearer <token>"
```

---

## Rollback/Recovery

If recovery fails:

1. **Stop the recovery**
2. **Preserve current state** (don't delete partial recovery)
3. **Restore from pre-migration backup**
4. **Escalate to senior engineering**

---

## Escalation

**Escalate if:**
- Migration rollback fails
- Database restore fails
- Manual fix fails
- Application cannot start after recovery
- Recovery time exceeds RTO (4 hours)
- Data loss detected

**Escalation Path:**
1. Senior Engineering
2. Database Administrator
3. CTO

---

## Recovery Duration

**Expected Recovery Times:**

- Migration rollback: 1-3 minutes
- Database restore: 5-15 minutes
- Manual fix: 15-60 minutes
- Forward-only recovery: 15-60 minutes

**Target RTO:** 4 hours (current stage)
**Actual recovery time should be measured and documented**

---

## Post-Recovery Actions

1. **Document the recovery**
   - What failed
   - Why it failed
   - Recovery duration
   - Recovery method used
   - Verification results

2. **Investigate root cause**
   - Review migration script
   - Review migration logs
   - Check for data issues
   - Check for schema conflicts

3. **Prevent recurrence**
   - Add pre-deployment migration testing
   - Add migration validation
   - Add rollback testing
   - Improve migration scripts

4. **Update documentation**
   - Update runbook with lessons learned
   - Update migration procedures
   - Document migration constraints

---

## Monitoring During Recovery

### Metrics to Watch

- `database_health_status{database="postgresql"}` - Database health
- `http_request_duration_seconds` - Application latency
- `database_operation_failures_total` - Operation failures

### Logs to Monitor

```bash
# PostgreSQL logs
docker compose logs -f postgres

# Backend logs
docker compose logs -f backend

# Migration logs
docker compose exec backend alembic upgrade head --verbose
```

---

## References

- Alembic configuration: `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/alembic.ini`
- Migration scripts: `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/alembic/versions/`
- Backup scripts: `/Users/mohsenrassam/Desktop/Lumenly/backups/`
- Restore scripts: `/Users/mohsenrassam/Desktop/Lumenly/backups/`

---

## Current Migrations

**Migration History:**
1. `c852e39aaee2` - Initial migration (empty)
   - upgrade: pass
   - downgrade: pass
   - Risk: LOW

2. `5123b1045ef3` - Users table
   - upgrade: create users table, indexes
   - downgrade: drop index, drop table (DATA LOSS)
   - Risk: MEDIUM

**Migration Safety:**
- Migration 5123b1045ef3 downgrade causes data loss
- Downgrade should be avoided if possible
- Forward-only recovery recommended for this migration

---

## Pre-Deployment Checklist

- [ ] Migration script reviewed
- [ ] Migration tested on staging
- [ ] Pre-migration backup created
- [ ] Rollback procedure documented
- [ ] Data migration requirements identified
- [ ] Migration duration estimated
- [ ] Application downtime planned (if needed)

---

## Migration Best Practices

1. **Always create pre-migration backup**
2. **Test migrations on staging first**
3. **Make migrations idempotent**
4. **Avoid destructive operations in downgrade**
5. **Document migration constraints**
6. **Test rollback if safe**
7. **Use transactions where possible**
8. **Add data validation after migration**

---

**Runbook Version:** 1.0
**Last Updated:** 2026-09-01
**Maintained By:** SRE Team
