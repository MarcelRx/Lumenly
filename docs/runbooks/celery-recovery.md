# Celery Recovery Runbook

## Overview

This runbook covers Celery task queue recovery procedures for Lumenly. Celery is used for asynchronous document processing, memory operations, and coaching tasks.

---

## Architecture

**Current Architecture:**
- **Broker:** Redis
- **Result Backend:** Redis
- **Worker Type:** Synchronous (prefork)
- **Concurrency:** Multiple workers
- **Task Visibility:** Redis

**Important:** Celery workers remain synchronous. No async event-loop architecture.

---

## Symptoms

Celery may need recovery if:
- Worker process crashes
- Worker becomes unresponsive
- Tasks not processing
- Task queue backlog
- Redis broker unavailable
- Result backend unavailable

---

## Detection

### Health Check Failure

```bash
curl http://localhost:8000/health/ready
```

**Expected:** `{"status":"healthy","checks":{"celery":"healthy",...}}`

**Failure:** `{"status":"unhealthy","checks":{"celery":"unhealthy",...}}`

### Application Errors

- Task submission failures in logs
- "No workers available" errors
- Task timeout errors
- Worker heartbeat failures

### Monitoring Alerts

- `CeleryWorkerUnavailable` (P0) - Worker completely unavailable
- `CeleryTaskBacklog` (P1) - Task queue backlog
- `HighHTTPLatencyP95` (P1) - Possible Celery performance issue

---

## Recovery Procedures

### Procedure 1: Worker Restart (Standard Recovery)

**Use when:** Worker process crashed or unresponsive

**Steps:**

1. **Check Celery Worker Status**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/.docker
   docker compose ps celery-worker
   ```

2. **View Worker Logs**
   ```bash
   docker compose logs celery-worker
   ```

3. **Restart Worker**
   ```bash
   docker compose restart celery-worker
   ```

4. **Verify Worker is Running**
   ```bash
   docker compose ps celery-worker
   docker compose logs celery-worker
   ```

5. **Verify Worker Connectivity**
   ```bash
   # Check worker logs for successful startup
   docker compose logs --tail=50 celery-worker
   ```

6. **Verify Application Health**
   ```bash
   curl http://localhost:8000/health/ready
   ```

**Expected Result:** All checks show "healthy"

---

### Procedure 2: Redis Broker Recovery

**Use when:** Redis broker unavailable (see Redis Recovery Runbook)

**Steps:**

1. **Recover Redis** (see `redis-recovery.md`)

2. **Restart Celery Worker**
   ```bash
   docker compose restart celery-worker
   ```

3. **Verify Worker Connectivity**
   ```bash
   docker compose logs celery-worker
   ```

4. **Check Task Queue**
   ```bash
   # Via application metrics
   curl http://localhost:8000/v1/metrics | grep celery
   ```

**Expected Result:** Worker connects to Redis, tasks processing

---

### Procedure 3: Task Queue Clear (Clean Slate)

**Use when:** Task queue corrupted or need fresh start

**Steps:**

1. **Stop Celery Worker**
   ```bash
   docker compose stop celery-worker
   ```

2. **Clear Redis Celery Keys**
   ```bash
   docker compose exec redis redis-cli
   
   # Clear Celery keys
   KEYS celery*
   
   # Delete Celery keys (CAUTION: loses all queued tasks)
   DEL celery*
   
   # Or delete specific queues
   DEL celery:default
   DEL celery:memory
   DEL celery:document_processing
   
   exit
   ```

3. **Start Celery Worker**
   ```bash
   docker compose start celery-worker
   ```

4. **Verify Worker**
   ```bash
   docker compose logs celery-worker
   ```

**Impact:** All queued tasks lost, in-flight tasks lost

---

### Procedure 4: Failed Task Recovery

**Use when:** Specific tasks failed and need retry

**Steps:**

1. **Identify Failed Tasks**
   ```bash
   # Check application logs
   docker compose logs backend | grep "Task failed"
   
   # Check Celery logs
   docker compose logs celery-worker | grep "Task failed"
   ```

2. **Retry Failed Tasks** (Application-Specific)
   - Document processing: Re-trigger document upload
   - Memory operations: Re-trigger memory operation
   - Coaching: Re-trigger coaching session

3. **Verify Task Completion**
   ```bash
   # Monitor Celery logs
   docker compose logs -f celery-worker
   ```

---

### Procedure 5: Worker Scaling Recovery

**Use when:** Worker overloaded, need more capacity

**Steps:**

1. **Check Worker Load**
   ```bash
   # Check Celery metrics
   curl http://localhost:8000/v1/metrics | grep celery
   ```

2. **Scale Workers** (via Docker Compose)
   ```bash
   # Edit docker-compose.yml to increase worker count
   # Then restart
   docker compose up -d --scale celery-worker=3
   ```

3. **Verify Workers**
   ```bash
   docker compose ps celery-worker
   ```

---

## Verification

### Worker Level Verification

```bash
# Check worker status
docker compose ps celery-worker

# Check worker logs
docker compose logs celery-worker

# Check worker connectivity to Redis
docker compose exec celery-worker python -c "from app.core.celery_app import celery; print(celery.control.ping())"
```

### Application Level Verification

```bash
# Health check
curl http://localhost:8000/health/ready

# Submit test task (if endpoint exists)
curl -X POST http://localhost:8000/api/tasks/test \
  -H "Authorization: Bearer <token>"
```

### Task Queue Verification

```bash
# Check Redis queue length
docker compose exec redis redis-cli
LLEN celery:default
LLEN celery:memory
LLEN celery:document_processing
exit

# Check Celery metrics
curl http://localhost:8000/v1/metrics | grep celery
```

---

## Rollback/Recovery

If recovery fails:

1. **Stop the recovery**
2. **Preserve current state** (don't delete data unnecessarily)
3. **Check Celery logs for errors**
4. **Check Redis connectivity**
5. **Check worker configuration**
6. **Escalate to senior engineering**

---

## Escalation

**Escalate if:**
- Worker repeatedly crashes
- Worker cannot connect to Redis
- Tasks not processing after restart
- Task queue continuously growing
- Recovery time exceeds 15 minutes

**Escalation Path:**
1. Senior Engineering
2. CTO

---

## Recovery Duration

**Expected Recovery Times:**

- Worker restart: 30 seconds - 2 minutes
- Redis broker recovery: 2-5 minutes
- Task queue clear: 1-3 minutes
- Failed task retry: 5-15 minutes

**Target RTO:** 15 minutes (Celery is not critical for core functionality)
**Actual recovery time should be measured and documented**

---

## Post-Recovery Actions

1. **Document the recovery**
   - What failed
   - Why it failed
   - Recovery duration
   - Tasks lost
   - Verification results

2. **Investigate root cause**
   - Review Celery logs
   - Check Redis logs
   - Check memory usage
   - Check for OOM kills

3. **Prevent recurrence**
   - Add monitoring
   - Add alerts
   - Adjust worker count
   - Add retry logic

4. **Update documentation**
   - Update runbook with lessons learned
   - Update recovery procedures

---

## Monitoring During Recovery

### Metrics to Watch

- `celery_workers_available` - Worker count
- `celery_tasks_total` - Task throughput
- `celery_task_failures_total` - Task failures
- `celery_task_backlog` - Queue backlog
- `database_health_status{database="redis"}` - Redis health

### Logs to Monitor

```bash
# Celery worker logs
docker compose logs -f celery-worker

# Backend logs
docker compose logs -f backend

# Redis logs
docker compose logs -f redis
```

---

## Task Idempotency

**Critical:** Tasks must be idempotent to allow safe retry.

**Verification:**
- Document processing tasks should handle duplicate processing
- Memory operations should handle duplicate execution
- Coaching tasks should handle duplicate execution

**Testing:**
- Submit same task twice
- Verify no duplicate data created
- Verify no errors on second execution

---

## Task Retry Behavior

**Current Configuration:**
- Retry on failure: YES
- Max retries: 3
- Retry delay: Exponential backoff

**Permanent Failure Handling:**
- After max retries, task marked as failed
- Error logged
- Application may alert or notify

**Verification:**
- Test task failure
- Verify retry behavior
- Verify permanent failure handling

---

## Synchronous Architecture Verification

**Critical:** Celery workers must remain synchronous (no async event-loop).

**Verification:**
```bash
# Search for async patterns in worker code
grep -r "asyncio" apps/backend/app/workers/
grep -r "new_event_loop" apps/backend/app/workers/
grep -r "run_until_complete" apps/backend/app/workers/
grep -r "ThreadPoolExecutor" apps/backend/app/workers/
```

**Expected:** No async patterns found in worker execution paths

---

## References

- Celery app: `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/app/core/celery_app.py`
- Worker tasks: `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/app/workers/tasks.py`
- Memory worker: `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/app/workers/memory_worker.py`
- Docker Compose: `/Users/mohsenrassam/Desktop/Lumenly/.docker/docker-compose.yml`

---

## Data Loss Impact

### Queued Tasks Lost
- **Impact:** Tasks not executed
- **Duration:** Until tasks re-triggered
- **Severity:** MEDIUM
- **Recovery:** Re-trigger tasks via application

### In-Flight Tasks Lost
- **Impact:** Tasks partially executed
- **Duration:** Until tasks re-triggered
- **Severity:** MEDIUM
- **Recovery:** Re-trigger tasks via application

### Task Results Lost
- **Impact:** Task results unavailable
- **Duration:** Until tasks re-executed
- **Severity:** LOW
- **Recovery:** Re-execute tasks

---

## Backup Strategy

**Backup Required:** NO

**Reasoning:**
- Task queue is ephemeral
- Tasks can be re-triggered
- Results can be re-computed
- Redis AOF provides crash recovery

---

**Runbook Version:** 1.0
**Last Updated:** 2026-09-01
**Maintained By:** SRE Team
