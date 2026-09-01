# High Error Rate Runbook

## Alert Meaning

The `HighHTTP5xxRate` alert fires when the HTTP 5xx error rate exceeds 5% for more than 5 minutes. This indicates sustained server-side errors affecting user requests.

## Severity

**P1 — HIGH**

## Immediate Checks

1. **Check current error rate:**
   ```bash
   curl -s http://localhost:9090/api/v1/query?query='sum(rate(http_requests_total{status_code=~"5.."}[5m]))/sum(rate(http_requests_total[5m]))'
   ```

2. **Check which endpoints are failing:**
   ```bash
   curl -s http://localhost:9090/api/v1/query?query='sum(rate(http_requests_total{status_code=~"5.."}[5m])) by (route)'
   ```

3. **Check backend logs for errors:**
   ```bash
   docker logs lumenly-backend --tail 500 | grep -i error
   ```

4. **Check dependency health:**
   ```bash
   curl http://localhost:8000/health/ready
   ```

## Relevant Logs

- Backend container logs: `docker logs lumenly-backend`
- Filter for 500-level errors in logs
- Check for exception stack traces

## Relevant Metrics

- `http_requests_total{status_code=~"5.."}` - 5xx request count
- `http_requests_total{status_code=~"4.."}` - 4xx request count
- `database_health_status` - Dependency health
- `database_operation_failures_total` - Database failures

## Health Endpoints

- `/health/ready` - Check if dependencies are healthy
- `/v1/metrics` - Prometheus metrics endpoint

## Safe Diagnostic Commands

```bash
# Check error rate by route
curl -s http://localhost:9090/api/v1/query?query='sum(rate(http_requests_total{status_code=~"5.."}[5m])) by (route)'

# Check database operation failures
curl -s http://localhost:9090/api/v1/query?query='sum(rate(database_operation_failures_total[5m])) by (database)'

# Check dependency health
curl http://localhost:8000/health/ready

# Check recent errors in logs
docker logs lumenly-backend --since 10m | grep -i "error\|exception"
```

## Recovery Procedure

1. **If dependencies are unhealthy:**
   - Follow the appropriate dependency runbook (PostgreSQL, MongoDB, Redis, Qdrant)
   - Wait for dependencies to recover
   - Monitor error rate

2. **If specific endpoint is failing:**
   - Identify the failing route from metrics
   - Check logs for that endpoint's errors
   - Review recent code changes for that endpoint
   - Consider rolling back recent deployments

3. **If database errors:**
   - Check database connection pools
   - Check for deadlocks or slow queries
   - Restart backend if connection pool is exhausted:
     ```bash
     docker-compose restart backend
     ```

4. **If LLM provider errors:**
   - Check LLM provider status
   - Check API key validity
   - Check rate limits on LLM provider

5. **If resource exhaustion:**
   - Check container resource usage: `docker stats lumenly-backend`
   - Scale up resources if needed
   - Check for memory leaks

## Escalation Conditions

Escalate if:
- Error rate exceeds 20% for more than 10 minutes
- All endpoints are failing
- Dependencies are healthy but error rate remains high
- Recent deployment correlates with error spike
- Database corruption suspected

## Additional Notes

- 5xx errors indicate server-side issues (not client errors)
- Check for recent code deployments
- Monitor the Grafana "API Overview" dashboard
- Check if the error is isolated to specific routes or system-wide
