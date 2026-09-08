# Redis Recovery Runbook

## Overview

This runbook covers Redis recovery procedures for Lumenly. Redis data is primarily ephemeral or reconstructible, so recovery is typically a restart operation.

---

## Symptoms

Redis may need recovery if:
- Redis process crashes
- Redis becomes unresponsive
- High memory usage causing eviction
- Network partition
- Disk full (AOF persistence)

---

## Detection

### Health Check Failure

```bash
curl http://localhost:8000/health/ready
```

**Expected:** `{"status":"healthy","checks":{"redis":"healthy",...}}`

**Failure:** `{"status":"unhealthy","checks":{"redis":"unhealthy",...}}`

### Application Errors

- Redis connection errors in logs
- Session failures
- Rate limiting errors
- Celery task queue errors

### Monitoring Alerts

- `RedisUnavailable` (P0) - Redis completely unavailable
- `HighHTTPLatencyP95` (P1) - Possible Redis performance issue

---

## Data Classification

### Redis Data Categories

| Category | Criticality | Reconstructible? | Recovery Strategy |
|----------|-------------|------------------|-------------------|
| Sessions | LOW | YES | Users re-authenticate |
| Rate Limiting | LOW | YES | Reset counters |
| Celery Broker | MEDIUM | PARTIAL | Tasks can be retried |
| Celery Results | LOW | YES | Re-execute tasks |
| Cache | LOW | YES | Rebuild cache |

### Detailed Analysis

**Sessions (JWT Refresh Tokens)**
- **Criticality:** LOW
- **Reconstructible:** YES
- **Loss Impact:** Users must re-authenticate
- **Recovery:** Users log in again, new tokens issued

**Rate Limiting**
- **Criticality:** LOW
- **Reconstructible:** YES
- **Loss Impact:** Counters reset, rate limits reset
- **Recovery:** Start fresh counters

**Celery Broker (Task Queue)**
- **Criticality:** MEDIUM
- **Reconstructible:** PARTIAL
- **Loss Impact:** Queued tasks lost, in-flight tasks lost
- **Recovery:** Tasks can be retried by application logic

**Celery Result Backend**
- **Criticality:** LOW
- **Reconstructible:** YES
- **Loss Impact:** Task results lost
- **Recovery:** Re-execute tasks

**Short-term Memory Cache**
- **Criticality:** LOW
- **Reconstructible:** YES
- **Loss Impact:** Conversation context lost
- **Recovery:** Conversations restart

---

## Recovery Procedures

### Procedure 1: Redis Restart (Standard Recovery)

**Use when:** Redis process crashed or unresponsive

**Steps:**

1. **Check Redis Status**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/.docker
   docker compose ps redis
   ```

2. **View Redis Logs**
   ```bash
   docker compose logs redis
   ```

3. **Restart Redis**
   ```bash
   docker compose restart redis
   ```

4. **Verify Redis is Running**
   ```bash
   docker compose ps redis
   docker compose logs redis
   ```

5. **Test Redis Connectivity**
   ```bash
   docker compose exec redis redis-cli ping
   ```
   **Expected:** `PONG`

6. **Verify Application Health**
   ```bash
   curl http://localhost:8000/health/ready
   ```

**Expected Result:** All checks show "healthy"

---

### Procedure 2: Redis Data Clear (Clean Slate)

**Use when:** Redis data corrupted or need fresh start

**Steps:**

1. **Stop Redis**
   ```bash
   cd /Users/mohsenrassam/Desktop/Lumenly/.docker
   docker compose stop redis
   ```

2. **Clear Redis Data Volume**
   ```bash
   # Option A: Delete volume (complete data loss)
   docker volume rm docker_redis_data
   
   # Option B: Clear data in container (safer)
   docker compose exec redis redis-cli FLUSHALL
   ```

3. **Start Redis**
   ```bash
   docker compose start redis
   ```

4. **Verify Redis is Running**
   ```bash
   docker compose ps redis
   docker compose exec redis redis-cli ping
   ```

5. **Restart Application**
   ```bash
   docker compose restart backend celery-worker
   ```

6. **Verify Application Health**
   ```bash
   curl http://localhost:8000/health/ready
   ```

**Impact:** All sessions lost, rate limits reset, Celery queue cleared

---

### Procedure 3: Celery Queue Recovery

**Use when:** Celery tasks lost after Redis failure

**Steps:**

1. **Restart Redis** (see Procedure 1)

2. **Restart Celery Worker**
   ```bash
   docker compose restart celery-worker
   ```

3. **Verify Celery Worker**
   ```bash
   docker compose logs celery-worker
   ```

4. **Re-queue Lost Tasks** (Application-Specific)
   - Document processing tasks may need to be re-triggered
   - Memory operations may need to be re-executed
   - Check application logs for task failures

5. **Verify Task Processing**
   ```bash
   # Monitor Celery metrics
   curl http://localhost:8000/v1/metrics | grep celery
   ```

---

### Procedure 4: Session Recovery

**Use when:** Users need to re-authenticate after Redis failure

**Steps:**

1. **Inform Users** (if applicable)
   - "Session expired, please log in again"

2. **Users Re-Authenticate**
   - Users log in via `/api/auth/login`
   - New JWT tokens issued
   - New refresh tokens stored in Redis

3. **Verify Authentication**
   ```bash
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"test"}'
   ```

**No manual intervention required** - users simply re-authenticate

---

## Verification

### Redis Level Verification

```bash
# Enter Redis CLI
docker compose exec redis redis-cli

# Test connectivity
ping

# Check memory usage
INFO memory

# Check connected clients
INFO clients

# Check persistence
INFO persistence

# Exit
exit
```

### Application Level Verification

```bash
# Health check
curl http://localhost:8000/health/ready

# Test rate limiting (should work)
curl http://localhost:8000/api/test

# Test authentication (should work)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'
```

### Celery Verification

```bash
# Check Celery worker logs
docker compose logs celery-worker

# Check Celery metrics
curl http://localhost:8000/v1/metrics | grep celery
```

---

## Rollback/Recovery

If recovery fails:

1. **Stop the recovery**
2. **Preserve current state** (don't delete data unnecessarily)
3. **Check Redis logs for errors**
4. **Check disk space**
5. **Escalate to senior engineering**

---

## Escalation

**Escalate if:**
- Redis repeatedly crashes
- Redis cannot start after restart
- Application cannot connect to Redis after restart
- Celery worker cannot connect to Redis
- Recovery time exceeds 15 minutes

**Escalation Path:**
1. Senior Engineering
2. CTO

---

## Recovery Duration

**Expected Recovery Times:**

- Redis restart: 30 seconds - 2 minutes
- Redis data clear: 2-5 minutes
- Celery queue recovery: 5-10 minutes

**Target RTO:** 15 minutes (Redis is not critical data)
**Actual recovery time should be measured and documented**

---

## Post-Recovery Actions

1. **Document the recovery**
   - What failed
   - Why it failed
   - Recovery duration
   - Data loss impact

2. **Investigate root cause**
   - Review Redis logs
   - Check memory usage
   - Check disk space
   - Check for OOM kills

3. **Prevent recurrence**
   - Add monitoring
   - Add alerts
   - Adjust memory limits
   - Add persistence configuration

4. **Update documentation**
   - Update runbook with lessons learned
   - Update recovery procedures

---

## Monitoring During Recovery

### Metrics to Watch

- `database_health_status{database="redis"}` - Redis health
- `redis_memory_usage_bytes` - Memory usage
- `redis_connected_clients` - Connected clients
- `http_request_duration_seconds` - Application latency

### Logs to Monitor

```bash
# Redis logs
docker compose logs -f redis

# Backend logs
docker compose logs -f backend

# Celery worker logs
docker compose logs -f celery-worker
```

---

## AOF Persistence

**Current Configuration:**
- AOF (Append Only File) enabled
- AOF provides crash recovery
- AOF is NOT a backup

**AOF Recovery:**
If Redis crashes with AOF enabled:
1. Redis automatically replays AOF on startup
2. Data is recovered to last AOF write
3. No manual intervention required

**AOF is NOT a backup because:**
- No point-in-time recovery
- No retention policy
- No separate storage
- Same disk as Redis

---

## Backup Strategy

**Backup Required:** NO

**Reasoning:**
- All Redis data is ephemeral or reconstructible
- Sessions: Users can re-authenticate
- Rate limiting: Counters can be reset
- Celery: Tasks can be retried
- Cache: Can be rebuilt

**Future Consideration:**
If Redis is used for critical persistent data in the future:
- Implement RDB snapshots
- Implement AOF rewrite
- Implement backup to external storage
- Implement retention policy

---

## References

- Docker Compose: `/Users/mohsenrassam/Desktop/Lumenly/.docker/docker-compose.yml`
- Redis configuration: Docker Compose redis service
- Application Redis client: `/Users/mohsenrassam/Desktop/Lumenly/apps/backend/app/db/redis.py`

---

## Data Loss Impact

### Sessions
- **Impact:** Users must re-authenticate
- **Duration:** 30 seconds - 2 minutes
- **Severity:** LOW

### Rate Limiting
- **Impact:** Rate limits reset
- **Duration:** Immediate
- **Severity:** LOW

### Celery Broker
- **Impact:** Queued tasks lost
- **Duration:** 5-10 minutes (re-queue tasks)
- **Severity:** MEDIUM

### Cache
- **Impact:** Cache miss, slower queries
- **Duration:** Until cache rebuilt
- **Severity:** LOW

---

**Runbook Version:** 1.0
**Last Updated:** 2026-09-01
**Maintained By:** SRE Team
