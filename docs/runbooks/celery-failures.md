# Celery Failures Runbook

## Alert Meaning

The `HighCeleryTaskFailureRate` alert fires when Celery task failure rate exceeds 10% for more than 5 minutes. This indicates background tasks are failing at an elevated rate.

## Severity

**P1 — HIGH**

## Immediate Checks

1. **Check Celery worker status:**
   ```bash
   docker ps | grep celery-worker
   ```

2. **Check Celery worker logs:**
   ```bash
   docker logs lumenly-celery-worker --tail 100
   ```

3. **Check current task failure rate:**
   ```bash
   curl -s http://localhost:9090/api/v1/query?query='sum(rate(celery_task_failures_total[5m]))/sum(rate(celery_tasks_total[5m]))'
   ```

4. **Check which tasks are failing:**
   ```bash
   curl -s http://localhost:9090/api/v1/query?query='sum(rate(celery_task_failures_total[5m])) by (failure_type)'
   ```

## Relevant Logs

- Celery worker container logs: `docker logs lumenly-celery-worker`
- Backend container logs: `docker logs lumenly-backend`

## Relevant Metrics

- `celery_tasks_total` - Total task executions
- `celery_task_failures_total` - Task failures
- `celery_task_retries_total` - Task retries
- `celery_task_duration_seconds` - Task duration

## Health Endpoints

- Celery worker health check (configured in docker-compose.yml)

## Safe Diagnostic Commands

```bash
# Check Celery worker status
docker inspect lumenly-celery-worker

# Check Celery worker is responsive
docker exec lumenly-celery-worker celery -A app.core.celery_app inspect ping

# Check active queues
docker exec lumenly-celery-worker celery -A app.core.celery_app inspect active_queues

# Check scheduled tasks
docker exec lumenly-celery-worker celery -A app.core.celery_app inspect scheduled

# Check worker resource usage
docker stats lumenly-celery-worker --no-stream
```

## Recovery Procedure

1. **If Celery worker is not running:**
   ```bash
   docker-compose up -d celery-worker
   ```

2. **If Celery worker is crashing:**
   - Check logs for error messages
   - Verify Redis is accessible (Celery broker)
   - Check for unhandled exceptions in tasks
   - Restart the service:
     ```bash
     docker-compose restart celery-worker
     ```

3. **If specific task type is failing:**
   - Identify the failing task from metrics
   - Check logs for that task's errors
   - Review recent code changes for that task
   - Check if dependencies for that task are available

4. **If Redis broker issues:**
   - Check Redis health: follow Redis runbook
   - Verify REDIS_URL environment variable
   - Check if Redis has sufficient memory

5. **If task duration is too long:**
   - Check task duration metrics
   - Check for long-running database queries
   - Consider increasing task timeout if appropriate
   - Optimize task implementation

6. **If retry limit exceeded:**
   - Check retry count metrics
   - Consider increasing retry limit if transient failures
   - Fix underlying issue causing retries

## Escalation Conditions

Escalate if:
- Task failure rate exceeds 50% for more than 10 minutes
- All task types are failing
- Celery worker cannot be restarted after 3 attempts
- Tasks are stuck in pending state
- Redis broker is unavailable
- The issue affects critical background processing

## Additional Notes

- Celery is used for document processing, memory operations, and coaching operations
- Celery uses Redis as both broker and backend
- Check the `depends_on` condition in docker-compose.yml
- Verify the REDIS_URL environment variable is correctly set
- Celery architecture is synchronous (do not introduce async/await)
- Check task queues: document_processing, memory_operations, coaching_operations
- Consider scaling up Celery workers if backlog is growing
