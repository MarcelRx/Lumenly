# MongoDB Unavailable Runbook

## Alert Meaning

The `MongoDBUnavailable` alert fires when MongoDB database health check fails for more than 2 minutes. This indicates the backend cannot connect to or query MongoDB.

## Severity

**P0 — CRITICAL**

## Immediate Checks

1. **Check MongoDB container status:**
   ```bash
   docker ps | grep mongo
   ```

2. **Check MongoDB logs:**
   ```bash
   docker logs lumenly-mongo --tail 100
   ```

3. **Check if MongoDB is accepting connections:**
   ```bash
   docker exec lumenly-mongo mongosh --eval "db.adminCommand('ping')"
   ```

4. **Check backend dependency health:**
   ```bash
   curl http://localhost:8000/health/ready
   ```

## Relevant Logs

- MongoDB container logs: `docker logs lumenly-mongo`
- Backend container logs: `docker logs lumenly-backend`

## Relevant Metrics

- `database_health_status{database="mongodb"}` - MongoDB health status
- `database_operation_failures_total{database="mongodb"}` - MongoDB failures

## Health Endpoints

- `/health/ready` - Backend readiness check (includes MongoDB)

## Safe Diagnostic Commands

```bash
# Check MongoDB container status
docker inspect lumenly-mongo

# Check MongoDB is ready
docker exec lumenly-mongo mongosh --eval "db.adminCommand('ping')"

# Check MongoDB replica set status
docker exec lumenly-mongo mongosh --eval "rs.status()"

# Check MongoDB resource usage
docker stats lumenly-mongo --no-stream

# Check disk space
docker exec lumenly-mongo df -h
```

## Recovery Procedure

1. **If MongoDB container is not running:**
   ```bash
   docker-compose up -d mongo
   ```

2. **If MongoDB container is crashing:**
   - Check logs for error messages
   - Verify disk space is available
   - Check for corrupted data files
   - Restart the service:
     ```bash
     docker-compose restart mongo
     ```

3. **If MongoDB is running but not accepting connections:**
   - Check if replica set is healthy
   - Check for connection limits
   - Restart MongoDB if necessary

4. **If network issues:**
   - Check Docker network: `docker network ls`
   - Check if backend can reach MongoDB:
     ```bash
     docker exec lumenly-backend ping mongo
     ```

5. **If replica set issues:**
   - Check replica set status: `docker exec lumenly-mongo mongosh --eval "rs.status()"`
   - Reconfigure replica set if needed
   - Check if all replica set members are available

## Escalation Conditions

Escalate immediately if:
- MongoDB cannot be restarted after 3 attempts
- Logs indicate database corruption
- Data loss is suspected
- Replica set cannot be reconfigured
- Disk is full and cannot be cleaned up
- The issue affects production users

## Additional Notes

- MongoDB is used for document storage and vector metadata
- Critical for memory consolidation, behavior aggregation
- Check the `depends_on` condition in docker-compose.yml
- Verify the MONGODB_URL environment variable is correctly set
- Replica set configuration is required for MongoDB
- Consider implementing automated backups if not already in place
