# LLM Provider Failure Runbook

## Alert Meaning

The `HighLLMFailureRate` alert fires when LLM request failure rate exceeds 10% for more than 5 minutes. The `LLMProviderUnavailable` alert fires when all LLM providers are unavailable for more than 5 minutes.

## Severity

**P0 — CRITICAL** (all providers unavailable), **P1 — HIGH** (high failure rate)

## Immediate Checks

1. **Check current LLM failure rate:**
   ```bash
   curl -s http://localhost:9090/api/v1/query?query='sum(rate(llm_request_failures_total[5m])) by (provider)/sum(rate(llm_requests_total[5m])) by (provider)'
   ```

2. **Check which provider is failing:**
   ```bash
   curl -s http://localhost:9090/api/v1/query?query='sum(rate(llm_request_failures_total[5m])) by (provider, failure_type)'
   ```

3. **Check LLM request latency:**
   ```bash
   curl -s http://localhost:9090/api/v1/query?query='histogram_quantile(0.95, sum(rate(llm_request_duration_seconds_bucket[5m])) by (le, provider))'
   ```

4. **Check if MockLLM is being used:**
   ```bash
   curl -s http://localhost:9090/api/v1/query?query='sum(llm_requests_total{provider="mock"})'
   ```

## Relevant Logs

- Backend container logs: `docker logs lumenly-backend`
- Look for LLM provider errors
- Check for API key errors

## Relevant Metrics

- `llm_requests_total` - Total LLM requests
- `llm_request_failures_total` - LLM failures
- `llm_request_duration_seconds` - LLM latency
- `llm_input_tokens_total` - Input tokens
- `llm_output_tokens_total` - Output tokens

## Health Endpoints

- `/health/ready` - Backend readiness (does not check LLM providers)
- `/v1/metrics` - Prometheus metrics

## Safe Diagnostic Commands

```bash
# Check LLM request volume by provider
curl -s http://localhost:9090/api/v1/query?query='sum(rate(llm_requests_total[5m])) by (provider)'

# Check LLM failure rate by provider
curl -s http://localhost:9090/api/v1/query?query='sum(rate(llm_request_failures_total[5m])) by (provider, failure_type)'

# Check LLM latency by provider
curl -s http://localhost:9090/api/v1/query?query='histogram_quantile(0.95, sum(rate(llm_request_duration_seconds_bucket[5m])) by (le, provider))'

# Check for MockLLM usage
curl -s http://localhost:9090/api/v1/query?query='sum(llm_requests_total{provider="mock"})'
```

## Recovery Procedure

1. **If API key issues:**
   - Verify GROQ_API_KEY environment variable
   - Verify GEMINI_API_KEY environment variable
   - Check if API keys are valid and not expired
   - Update API keys if needed:
     ```bash
     docker-compose restart backend
     ```

2. **If provider is down:**
   - Check provider status page (Groq, Gemini)
   - Check if provider is experiencing outage
   - Wait for provider to recover
   - Consider switching to backup provider if available

3. **If rate limiting:**
   - Check if hitting provider rate limits
   - Check token usage metrics
   - Consider implementing request queuing
   - Consider upgrading provider plan if needed

4. **If MockLLM is detected:**
   - **CRITICAL:** MockLLM should never be used in production
   - Check EMBEDDING_PROVIDER environment variable
   - Check LLM provider configuration
   - Ensure production environment variables are set correctly
   - Restart backend with correct configuration

5. **If network issues:**
   - Check if backend can reach LLM provider APIs
   - Check DNS resolution
   - Check firewall rules
   - Check proxy settings if applicable

6. **If timeout issues:**
   - Check LLM latency metrics
   - Increase timeout if provider is slow
   - Check if requests are too large
   - Consider streaming responses if supported

## Escalation Conditions

Escalate immediately if:
- All LLM providers are unavailable for more than 10 minutes
- MockLLM is detected in production
- API keys are invalid or expired
- Provider is experiencing widespread outage
- The issue affects production users

## Additional Notes

- LLM providers: Groq, Gemini
- MockLLM is for testing only - never use in production
- Verify GROQ_API_KEY and GEMINI_API_KEY environment variables
- Check the Grafana "AI / LLM" dashboard for trends
- Monitor token consumption to avoid unexpected costs
- Consider implementing fallback provider if one fails
- LLM failures will degrade RAG and AI coaching features
