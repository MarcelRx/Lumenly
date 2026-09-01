# Redis Unavailable Runbook

## Alert Meaning

The `RedisUnavailable` alert fires when Redis cache health check fails for more than 2 minutes. This indicates the backend cannot connect to Redis.

## Severity

**P0 — CRITICAL**

## Immediate Checks

1. **Check Redis container status:**
   ```bash
   docker ps | grep redis
   ```

2. **Check Redis logs:**
   ```bash
   docker logs lumenly-redis --tail 100
   ```

3. **Check if Redis is accepting connections:**
   ```bash
   docker exec lumenly-redis redis-cli ping
   ```

4. **Check backend dependency health:**
   ```bash
   curl http://localhost:8000/health/ready
   ```

## Relevant Logs

- Redis container logs: `docker logs lumenly-redis`
- Backend container logs: `docker logs lumenly-backend`

## Relevant Metrics

- `database_health_status{database="redis"}` - Redis health status
- `database_operation_failures_total{database="redis"}` - Redis failures

## Health Endpoints

- `/health/ready` - Backend readiness check (includes Redis)

## Safe Diagnostic Commands

```bash
# Check Redis container status
docker inspect lumenly-redis

# Check Redis is ready
docker exec lumenly-redis redis-cli ping

# Check Redis info
docker exec lumenly-redis redis-cli info

# Check Redis memory usage
docker exec lumenly-redis redis-cli info memory

# Check Redis resource usage
docker stats lumenly-redis --no-stream

# Check disk space
docker exec lumenly-redis df -h
```

## Recovery Procedure

1. **If Redis container is not running:**
   ```bash
   docker-compose up -d redis
   ```

2. **If Redis container is crashing:**
   - Check logs for error messages
   - Verify disk space is available
   - Check if maxmemory limit is reached
   - Restart the service:
     ```bash
     docker-compose restart redis
     ```

3. **If Redis is running but not accepting connections:**
   - Check if maxclients limit is reached
   - Check if Redis is in OOM (out of memory) state
   - Restart Redis if necessary

4. **If network issues:**
   - Check Docker network: `docker network ls`
   - Check if backend can reach Redis:
     ```bash
     docker exec lumenly-backend ping redis
     ```

5. **If memory issues:**
   - Check Redis memory usage: `docker exec lumenly-redis redis-cli info memory`
   - Check if eviction policy is configured
   - Consider increasing memory limit if needed

## Escalation Conditions

Escalate immediately if:
- Redis cannot be restarted after 3 attempts
- Logs indicate data corruption
- Disk is full and cannot be cleaned up
- Memory limit cannot be increased
- The issue affects production users

## Additional Notes

- Redis is used for caching and rate limiting
- Critical for session management and rate limit enforcement
- Check the `depends_on` condition in docker-compose.yml
- Verify the REDIS_URL environment variable is correctly set
- Redis data is volatile (lost on restart) - this is expected
- Consider implementing persistence (AOF/RDB) if durability is required
