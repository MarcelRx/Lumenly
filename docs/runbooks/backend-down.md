# Backend Down Runbook

## Alert Meaning

The `BackendDown` alert fires when Prometheus cannot scrape the Lumenly backend service for more than 1 minute. This indicates the backend service is completely unavailable.

## Severity

**P0 — CRITICAL**

## Immediate Checks

1. **Check if the backend container is running:**
   ```bash
   docker ps | grep lumenly-backend
   ```

2. **Check backend container logs:**
   ```bash
   docker logs lumenly-backend --tail 100
   ```

3. **Check if the backend is listening on port 8000:**
   ```bash
   docker exec lumenly-backend netstat -tlnp | grep 8000
   ```

4. **Check backend health endpoint:**
   ```bash
   curl -f http://localhost:8000/health/live
   ```

## Relevant Logs

- Backend container logs: `docker logs lumenly-backend`
- Application logs (if using centralized logging)

## Relevant Metrics

- `up{job="lumenly-backend"}` - Target up status
- `http_requests_total` - Request count (should be 0 if down)
- `database_health_status` - Dependency health status

## Health Endpoints

- `/health/live` - Liveness probe
- `/health/ready` - Readiness probe

## Safe Diagnostic Commands

```bash
# Check container status
docker inspect lumenly-backend

# Check resource usage
docker stats lumenly-backend

# Check container restart count
docker inspect lumenly-backend | grep RestartCount

# Check if dependencies are healthy
docker ps | grep -E "postgres|mongo|redis|qdrant"
```

## Recovery Procedure

1. **If container is not running:**
   ```bash
   docker-compose up -d backend
   ```

2. **If container is crashing:**
   - Check logs for error messages
   - Verify environment variables are set correctly
   - Verify database connections are accessible
   - Restart the service:
     ```bash
     docker-compose restart backend
     ```

3. **If container is running but not responding:**
   - Check if the process is hung
   - Force restart:
     ```bash
     docker-compose restart backend
     ```

4. **If dependencies are unavailable:**
   - Check PostgreSQL, MongoDB, Redis, Qdrant status
   - Start/restart dependencies as needed
   - Restart backend after dependencies are healthy

## Escalation Conditions

Escalate immediately if:
- Backend cannot be restarted after 3 attempts
- All dependencies are healthy but backend still fails
- Logs indicate database corruption or data loss
- The issue affects production users

## Additional Notes

- The backend depends on PostgreSQL, MongoDB, Redis, and Qdrant
- Check the `depends_on` conditions in docker-compose.yml
- Verify the `SECRET_KEY` and other environment variables are set
- Check for recent code deployments that may have introduced bugs
