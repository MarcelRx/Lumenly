# PostgreSQL Unavailable Runbook

## Alert Meaning

The `PostgreSQLUnavailable` alert fires when PostgreSQL database health check fails for more than 2 minutes. This indicates the backend cannot connect to or query PostgreSQL.

## Severity

**P0 — CRITICAL**

## Immediate Checks

1. **Check PostgreSQL container status:**
   ```bash
   docker ps | grep postgres
   ```

2. **Check PostgreSQL logs:**
   ```bash
   docker logs lumenly-postgres --tail 100
   ```

3. **Check if PostgreSQL is accepting connections:**
   ```bash
   docker exec lumenly-postgres pg_isready
   ```

4. **Check backend dependency health:**
   ```bash
   curl http://localhost:8000/health/ready
   ```

## Relevant Logs

- PostgreSQL container logs: `docker logs lumenly-postgres`
- Backend container logs: `docker logs lumenly-backend`

## Relevant Metrics

- `database_health_status{database="postgresql"}` - PostgreSQL health status
- `database_operation_failures_total{database="postgresql"}` - PostgreSQL failures

## Health Endpoints

- `/health/ready` - Backend readiness check (includes PostgreSQL)

## Safe Diagnostic Commands

```bash
# Check PostgreSQL container status
docker inspect lumenly-postgres

# Check PostgreSQL is ready
docker exec lumenly-postgres pg_isready

# Check PostgreSQL connections
docker exec lumenly-postgres psql -U lumenly -d lumenly -c "SELECT version();"

# Check PostgreSQL resource usage
docker stats lumenly-postgres --no-stream

# Check disk space
docker exec lumenly-postgres df -h
```

## Recovery Procedure

1. **If PostgreSQL container is not running:**
   ```bash
   docker-compose up -d postgres
   ```

2. **If PostgreSQL container is crashing:**
   - Check logs for error messages
   - Verify disk space is available
   - Check for corrupted data files
   - Restart the service:
     ```bash
     docker-compose restart postgres
     ```

3. **If PostgreSQL is running but not accepting connections:**
   - Check if max_connections limit is reached
   - Check for long-running transactions blocking connections
   - Restart PostgreSQL if necessary

4. **If network issues:**
   - Check Docker network: `docker network ls`
   - Check if backend can reach PostgreSQL:
     ```bash
     docker exec lumenly-backend ping postgres
     ```

5. **If authentication issues:**
   - Verify POSTGRES_URL environment variable
   - Verify POSTGRES_USER and POSTGRES_PASSWORD
   - Check pg_hba.conf if custom configuration

## Escalation Conditions

Escalate immediately if:
- PostgreSQL cannot be restarted after 3 attempts
- Logs indicate database corruption
- Data loss is suspected
- Disk is full and cannot be cleaned up
- The issue affects production users

## Additional Notes

- PostgreSQL is the primary relational database for Lumenly
- Critical for user authentication, sessions, and structured data
- Check the `depends_on` condition in docker-compose.yml
- Verify the POSTGRES_URL environment variable is correctly set
- Consider implementing automated backups if not already in place
