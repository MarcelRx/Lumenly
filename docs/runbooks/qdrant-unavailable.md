# Qdrant Unavailable Runbook

## Alert Meaning

The `QdrantUnavailable` alert fires when Qdrant vector database health check fails for more than 2 minutes. This indicates the backend cannot connect to or query Qdrant.

## Severity

**P1 — HIGH** (Qdrant is important but not as critical as PostgreSQL/MongoDB/Redis)

## Immediate Checks

1. **Check Qdrant container status:**
   ```bash
   docker ps | grep qdrant
   ```

2. **Check Qdrant logs:**
   ```bash
   docker logs lumenly-qdrant --tail 100
   ```

3. **Check if Qdrant is accepting connections:**
   ```bash
   curl http://localhost:6333/health
   ```

4. **Check backend dependency health:**
   ```bash
   curl http://localhost:8000/health/ready
   ```

## Relevant Logs

- Qdrant container logs: `docker logs lumenly-qdrant`
- Backend container logs: `docker logs lumenly-backend`

## Relevant Metrics

- `database_health_status{database="qdrant"}` - Qdrant health status
- `database_operation_failures_total{database="qdrant"}` - Qdrant failures

## Health Endpoints

- `/health/ready` - Backend readiness check (includes Qdrant)
- `http://localhost:6333/health` - Qdrant health endpoint

## Safe Diagnostic Commands

```bash
# Check Qdrant container status
docker inspect lumenly-qdrant

# Check Qdrant health
curl http://localhost:6333/health

# Check Qdrant collections
curl http://localhost:6333/collections

# Check Qdrant resource usage
docker stats lumenly-qdrant --no-stream

# Check disk space
docker exec lumenly-qdrant df -h
```

## Recovery Procedure

1. **If Qdrant container is not running:**
   ```bash
   docker-compose up -d qdrant
   ```

2. **If Qdrant container is crashing:**
   - Check logs for error messages
   - Verify disk space is available
   - Check for corrupted data files
   - Restart the service:
     ```bash
     docker-compose restart qdrant
     ```

3. **If Qdrant is running but not accepting connections:**
   - Check if port 6333 is accessible
   - Check for connection limits
   - Restart Qdrant if necessary

4. **If network issues:**
   - Check Docker network: `docker network ls`
   - Check if backend can reach Qdrant:
     ```bash
     docker exec lumenly-backend ping qdrant
     ```

5. **If collection issues:**
   - Check if collections exist: `curl http://localhost:6333/collections`
   - Recreate collections if corrupted
   - Check vector dimension configuration

## Escalation Conditions

Escalate if:
- Qdrant cannot be restarted after 3 attempts
- Logs indicate data corruption
- Vector data loss is suspected
- Disk is full and cannot be cleaned up
- The issue affects production users for more than 30 minutes

## Additional Notes

- Qdrant is used for vector storage and similarity search
- Critical for RAG (Retrieval-Augmented Generation) functionality
- Check the `depends_on` condition in docker-compose.yml
- Verify the QDRANT_URL environment variable is correctly set
- Qdrant data persists in Docker volume: `qdrant_data`
- Consider implementing automated backups of vector data
- Without Qdrant, RAG features will be degraded or unavailable
