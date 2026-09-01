# Security Anomaly Runbook

## Alert Meaning

Security alerts fire when abnormal security-related activity is detected:
- `HighAuthenticationFailureRate` - Elevated authentication failures
- `HighAuthorizationFailureRate` - Elevated authorization failures
- `CrossTenantAccessAttempts` - Attempts to access data across tenants
- `HighRateLimitViolations` - Abnormal rate limit violations

## Severity

**P0 — CRITICAL** (cross-tenant attempts), **P1 — HIGH** (auth failures, rate limits)

## Immediate Checks

1. **Check authentication failure rate:**
   ```bash
   curl -s http://localhost:9090/api/v1/query?query='sum(rate(auth_login_attempts_total{result=~"invalid_credentials|inactive_user"}[5m]))'
   ```

2. **Check authorization failures:**
   ```bash
   curl -s http://localhost:9090/api/v1/query?query='sum(rate(security_authorization_failures_total[5m])) by (resource_type)'
   ```

3. **Check cross-tenant attempts:**
   ```bash
   curl -s http://localhost:9090/api/v1/query?query='sum(rate(security_cross_tenant_attempts_total[5m]))'
   ```

4. **Check rate limit violations:**
   ```bash
   curl -s http://localhost:9090/api/v1/query?query='sum(rate(security_rate_limit_exceeded_total[5m])) by (user_role)'
   ```

## Relevant Logs

- Backend container logs: `docker logs lumenly-backend`
- Look for authentication/authorization failures
- Look for cross-tenant access attempts
- Look for rate limit violations

## Relevant Metrics

- `auth_login_attempts_total` - Authentication attempts
- `security_authorization_failures_total` - Authorization failures
- `security_cross_tenant_attempts_total` - Cross-tenant attempts
- `security_rate_limit_exceeded_total` - Rate limit violations
- `rate_limit_violations_total` - General rate limit violations

## Health Endpoints

- `/health/ready` - Backend readiness
- `/v1/metrics` - Prometheus metrics

## Safe Diagnostic Commands

```bash
# Check authentication attempts by result
curl -s http://localhost:9090/api/v1/query?query='sum(rate(auth_login_attempts_total[5m])) by (result)'

# Check authorization failures by resource type
curl -s http://localhost:9090/api/v1/query?query='sum(rate(security_authorization_failures_total[5m])) by (resource_type)'

# Check cross-tenant attempts
curl -s http://localhost:9090/api/v1/query?query='sum(rate(security_cross_tenant_attempts_total[5m])) by (resource_type)'

# Check rate limit violations by user role
curl -s http://localhost:9090/api/v1/query?query='sum(rate(security_rate_limit_exceeded_total[5m])) by (user_role)'

# Check recent security events in logs
docker logs lumenly-backend --since 10m | grep -i "security\|authorization\|cross-tenant"
```

## Recovery Procedure

### High Authentication Failures

1. **If brute force attack suspected:**
   - Check if failures are from single IP or distributed
   - Consider implementing IP-based rate limiting
   - Consider implementing account lockout after N failures
   - Block malicious IPs if identified

2. **If credential leak suspected:**
   - Check if many accounts are failing
   - Consider forcing password reset for affected users
   - Check for recent data breaches
   - Review authentication logs for patterns

3. **If system issue:**
   - Check if JWT_SECRET is correctly configured
   - Check if JWT validation is working correctly
   - Check if authentication service is available

### High Authorization Failures

1. **If privilege escalation attempt:**
   - Check which resources are being accessed
   - Check which users are attempting access
   - Review permission configuration
   - Revoke suspicious permissions

2. **If configuration issue:**
   - Check if role-based access control is correct
   - Check if permissions were recently changed
   - Review recent code changes to authorization logic

### Cross-Tenant Access Attempts

**CRITICAL - Immediate Action Required**

1. **If cross-tenant attempts detected:**
   - **IMMEDIATELY** identify the affected user(s)
   - **IMMEDIATELY** revoke access for suspicious users
   - **IMMEDIATELY** review the access attempt logs
   - Check if this is a bug or malicious attack
   - If bug: fix immediately and deploy hotfix
   - If attack: block attacker, review all affected data

2. **Investigation:**
   - Review all cross-tenant attempts in logs
   - Identify all potentially exposed data
   - Notify affected users if data exposure confirmed
   - Review tenant isolation implementation

### High Rate Limit Violations

1. **If DDoS attack suspected:**
   - Check if violations are from single IP or distributed
   - Consider implementing IP-based blocking
   - Consider implementing CAPTCHA
   - Scale up resources if legitimate traffic spike

2. **If legitimate traffic spike:**
   - Check if rate limits are too strict
   - Consider increasing rate limits temporarily
   - Scale up infrastructure if needed

3. **If misconfiguration:**
   - Check if rate limit configuration is correct
   - Check if Redis is available (rate limit backend)
   - Review recent configuration changes

## Escalation Conditions

Escalate **IMMEDIATELY** if:
- Cross-tenant access attempts are detected (P0)
- Authentication failures indicate credential breach
- Authorization failures indicate privilege escalation
- Rate limit violations indicate DDoS attack
- Security bug is suspected in tenant isolation

## Additional Notes

- Security events are logged with request correlation IDs
- Check the Grafana "Security" dashboard for trends
- Review logs for patterns (IP addresses, user agents, etc.)
- Security incidents may require legal/compliance reporting
- Document all security incidents for post-mortem
- Consider implementing security monitoring service (e.g., Datadog Security)
- Never expose user IDs, emails, or other PII in alerts or dashboards
