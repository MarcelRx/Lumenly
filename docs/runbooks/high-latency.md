# High Latency Runbook

## Alert Meaning

The `HighHTTPLatencyP95` alert fires when the HTTP request P95 latency exceeds 1 second for more than 5 minutes. This indicates significant performance degradation affecting user experience.

## Severity

**P1 — HIGH** (for >1s), **P2 — WARNING** (for >500ms)

## Immediate Checks

1. **Check current P95 latency:**
   ```bash
   curl -s http://localhost:9090/api/v1/query?query='histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))'
   ```

2. **Check which routes have high latency:**
   ```bash
   curl -s http://localhost:9090/api/v1/query?query='histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, route))'
   ```

3. **Check backend resource usage:**
   ```bash
   docker stats lumenly-backend
   ```

4. **Check dependency health:**
   ```bash
   curl http://localhost:8000/health/ready
   ```

## Relevant Logs

- Backend container logs: `docker logs lumenly-backend`
- Look for slow query logs
- Check for timeout errors

## Relevant Metrics

- `http_request_duration_seconds` - Request latency histogram
- `database_operation_failures_total` - Database failures
- `llm_request_duration_seconds` - LLM provider latency
- `celery_task_duration_seconds` - Celery task duration

## Health Endpoints

- `/health/ready` - Check dependency health
- `/v1/metrics` - Prometheus metrics

## Safe Diagnostic Commands

```bash
# Check P95 latency by route
curl -s http://localhost:9090/api/v1/query?query='histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, route))'

# Check LLM latency
curl -s http://localhost:9090/api/v1/query?query='histogram_quantile(0.95, sum(rate(llm_request_duration_seconds_bucket[5m])) by (le, provider))'

# Check Celery task duration
curl -s http://localhost:9090/api/v1/query?query='histogram_quantile(0.95, sum(rate(celery_task_duration_seconds_bucket[5m])) by (le, task))'

# Check container resource usage
docker stats lumenly-backend --no-stream
```

## Recovery Procedure

1. **If specific route has high latency:**
   - Identify the slow route from metrics
   - Check if the route involves LLM calls
   - Check if the route involves database queries
   - Review recent code changes for that route

2. **If LLM latency is high:**
   - Check LLM provider status
   - Check if using a slower model
   - Consider switching to faster model if appropriate
   - Check for rate limiting on LLM provider

3. **If database latency is high:**
   - Check database performance: `docker exec postgres pg_stat_activity`
   - Check for slow queries
   - Check database resource usage
   - Consider adding indexes if needed

4. **If resource exhaustion:**
   - Check CPU/memory usage: `docker stats lumenly-backend`
   - Scale up resources if needed
   - Check for memory leaks

5. **If Celery tasks are slow:**
   - Check Celery worker status
   - Check if worker queue is backed up
   - Scale up Celery workers if needed

## Escalation Conditions

Escalate if:
- P95 latency exceeds 5 seconds for more than 10 minutes
- All routes are affected
- Dependencies are healthy but latency remains high
- Database performance degradation suspected
- LLM provider is experiencing widespread issues

## Additional Notes

- P95 latency means 95% of requests complete within this time
- Check the Grafana "API Overview" dashboard for latency trends
- Compare latency to baseline (normal operation)
- Check if latency spike correlates with traffic increase
- Consider if recent code changes introduced performance regression
