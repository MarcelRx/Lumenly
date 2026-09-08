# CI/CD Pipeline Design for Lumenly

## Overview

This document outlines the design for a production-safe CI/CD pipeline for Lumenly. The current deployment is manual via Docker Compose. This design provides a foundation for automated deployment with safety mechanisms.

---

## Current State

**Deployment Method:** Manual
- Docker Compose manual execution
- No automated tests
- No automated deployment
- No automated rollback
- No pre-deployment validation
- Empty `.github/workflows/` directory

**Limitations:**
- Human error risk
- No deployment history
- No rollback automation
- No deployment verification
- No security checks

---

## Proposed Pipeline Architecture

### Success Pipeline

```
Commit
 ↓
Trigger (push to main / PR)
 ↓
Unit Tests
 ↓
Integration Tests
 ↓
Security Scans
 ↓
Docker Build
 ↓
Image Validation
 ↓
Pre-Deployment Backup
 ↓
Migration Validation
 ↓
Deployment (Staging)
 ↓
Health Verification
 ↓
Smoke Tests
 ↓
Manual Approval (for production)
 ↓
Deployment (Production)
 ↓
Health Verification
 ↓
Smoke Tests
 ↓
Success
```

### Failure Pipeline

```
Deployment Failure
 ↓
Stop Deployment
 ↓
Alert
 ↓
Rollback
 ↓
Health Verification
 ↓
Investigation
 ↓
Fix
 ↓
Retry
```

---

## Pipeline Stages

### Stage 1: Validation

**Unit Tests**
- Run all unit tests
- Coverage threshold: 80%
- Fail if any test fails

**Integration Tests**
- Run integration tests
- Test database connectivity
- Test API endpoints
- Fail if any test fails

**Security Scans**
- Dependency scan (Snyk/Dependabot)
- Secret scan (TruffleHog)
- SAST (Static Application Security Testing)
- Fail if critical vulnerabilities found

### Stage 2: Build

**Docker Build**
- Build backend image
- Build celery-worker image
- Tag with commit SHA
- Tag with semantic version

**Image Validation**
- Verify image builds successfully
- Verify image size reasonable
- Verify no secrets in image
- Verify base image up-to-date

### Stage 3: Pre-Deployment

**Backup**
- Run PostgreSQL backup
- Run MongoDB backup
- Verify backup integrity
- Fail if backup fails

**Migration Validation**
- Check migration files exist
- Validate migration syntax
- Test migration on staging
- Fail if migration invalid

### Stage 4: Deployment (Staging)

**Deploy to Staging**
- Stop staging containers
- Pull new images
- Start staging containers
- Run migrations

**Health Verification**
- Check `/health/live`
- Check `/health/ready`
- Verify all dependencies healthy
- Fail if unhealthy

**Smoke Tests**
- Test authentication
- Test API endpoints
- Test database connectivity
- Fail if any test fails

### Stage 5: Manual Approval

**Production Deployment Gate**
- Require manual approval
- Display deployment summary
- Display backup location
- Display rollback plan
- Require confirmation

### Stage 6: Deployment (Production)

**Deploy to Production**
- Stop production containers
- Pull new images
- Start production containers
- Run migrations

**Health Verification**
- Check `/health/live`
- Check `/health/ready`
- Verify all dependencies healthy
- Fail if unhealthy

**Smoke Tests**
- Test authentication
- Test API endpoints
- Test database connectivity
- Fail if any test fails

---

## Rollback Pipeline

### Automatic Rollback Triggers

- Health check fails
- Smoke test fails
- Error rate exceeds threshold
- Latency exceeds threshold

### Rollback Steps

1. **Stop Deployment**
   - Stop new containers
   - Preserve failed state for investigation

2. **Rollback Application**
   - Revert to previous image
   - Restart containers

3. **Rollback Database** (if schema changed)
   - Restore from pre-deployment backup
   - Verify restore

4. **Health Verification**
   - Check `/health/live`
   - Check `/health/ready`
   - Verify all dependencies healthy

5. **Alert**
   - Notify engineering team
   - Create incident ticket

---

## GitHub Actions Workflow

### File: `.github/workflows/deploy.yml`

```yaml
name: Deploy Lumenly

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: lumenly-backend

jobs:
  test:
    name: Test
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd apps/backend
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run unit tests
        run: |
          cd apps/backend
          pytest tests/unit --cov=app --cov-report=xml --cov-fail-under=80
      
      - name: Run integration tests
        run: |
          cd apps/backend
          pytest tests/integration
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  security:
    name: Security Scan
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Run TruffleHog
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.base_ref }}
          head: HEAD
      
      - name: Run Snyk
        uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}

  build:
    name: Build
    runs-on: ubuntu-latest
    needs: [test, security]
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ./apps/backend
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  backup:
    name: Pre-Deployment Backup
    runs-on: ubuntu-latest
    needs: [build]
    if: github.ref == 'refs/heads/main'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Run PostgreSQL backup
        run: |
          # This would run on production server
          # For now, this is a placeholder
          echo "PostgreSQL backup would run here"
      
      - name: Run MongoDB backup
        run: |
          # This would run on production server
          # For now, this is a placeholder
          echo "MongoDB backup would run here"

  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: [backup]
    if: github.ref == 'refs/heads/main'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Deploy to staging
        run: |
          # This would deploy to staging environment
          # For now, this is a placeholder
          echo "Deploy to staging would run here"
      
      - name: Health verification
        run: |
          # This would verify health
          # For now, this is a placeholder
          echo "Health verification would run here"

  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [deploy-staging]
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://lumenly.example.com
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Manual approval
        uses: trstringer/manual-approval@v1
        with:
          secret: ${{ secrets.GITHUB_TOKEN }}
          approvers: senior-engineer,cto
          minimum-approvals: 1
      
      - name: Deploy to production
        run: |
          # This would deploy to production
          # For now, this is a placeholder
          echo "Deploy to production would run here"
      
      - name: Health verification
        run: |
          # This would verify health
          # For now, this is a placeholder
          echo "Health verification would run here"
      
      - name: Rollback on failure
        if: failure()
        run: |
          # This would rollback
          # For now, this is a placeholder
          echo "Rollback would run here"
```

---

## Deployment Strategy

### Current Strategy: Recreate Deployment

**Description:**
- Stop all containers
- Build new images
- Start all containers
- Downtime: 2-5 minutes

**Limitations:**
- Downtime required
- No rolling update
- No blue/green deployment

**Suitability:** Acceptable for current stage (early production)

### Future Strategy: Blue/Green Deployment

**Description:**
- Deploy new version to green environment
- Verify green environment
- Switch traffic to green
- Keep blue for rollback

**Benefits:**
- Zero downtime
- Instant rollback
- Safe deployment

**Requirements:**
- Load balancer
- Multiple environments
- Database migration compatibility

**Suitability:** Future requirement for high availability

---

## Migration Strategy

### Current Strategy: Stop-and-Go Migration

**Description:**
- Stop application
- Run migration
- Start application
- Downtime: 1-3 minutes

**Limitations:**
- Downtime required
- No zero-downtime migration

**Suitability:** Acceptable for current stage

### Future Strategy: Rolling Migration

**Description:**
- Deploy new application version
- Run migration
- Switch traffic
- Downtime: Minimal

**Requirements:**
- Backward-compatible migrations
- Multiple application versions
- Database migration compatibility

**Suitability:** Future requirement for high availability

---

## Safety Mechanisms

### Pre-Deployment Checks

- [ ] All tests pass
- [ ] Security scan passes
- [ ] Backup completed
- [ ] Migration validated
- [ ] Manual approval obtained

### Deployment Checks

- [ ] Health check passes
- [ ] Smoke tests pass
- [ ] Error rate normal
- [ ] Latency normal

### Rollback Triggers

- Health check fails
- Smoke test fails
- Error rate > 5%
- Latency > 2x baseline

---

## Monitoring Integration

### Metrics to Monitor

- `http_requests_total` - Request rate
- `http_request_duration_seconds` - Latency
- `http_request_failures_total` - Error rate
- `database_health_status` - Database health
- `celery_tasks_total` - Task throughput

### Alerts to Configure

- `DeploymentFailure` - Deployment failed
- `HighErrorRate` - Error rate elevated
- `HighLatency` - Latency elevated
- `DatabaseUnavailable` - Database down

---

## Secret Management

### Current Strategy: Environment Variables

**Description:**
- Secrets in `.env` files
- `.env` in `.gitignore`
- Secrets in Docker Compose environment variables

**Limitations:**
- Manual secret management
- No secret rotation
- No audit logging

**Suitability:** Acceptable for current stage

### Future Strategy: HashiCorp Vault

**Description:**
- Secrets in Vault
- Automatic secret injection
- Secret rotation
- Audit logging

**Benefits:**
- Automated secret management
- Secret rotation
- Audit logging

**Requirements:**
- Vault infrastructure
- Integration with CI/CD

**Suitability:** Future requirement for production

---

## Implementation Roadmap

### Phase 1: Foundation (Current)

- [x] Design CI/CD pipeline
- [ ] Create GitHub Actions workflow
- [ ] Configure automated tests
- [ ] Configure security scans
- [ ] Configure Docker build

### Phase 2: Deployment Automation

- [ ] Configure staging deployment
- [ ] Configure production deployment
- [ ] Configure manual approval
- [ ] Configure health verification
- [ ] Configure smoke tests

### Phase 3: Rollback Automation

- [ ] Configure automatic rollback triggers
- [ ] Configure rollback procedure
- [ ] Configure rollback verification
- [ ] Test rollback

### Phase 4: Advanced Features

- [ ] Configure blue/green deployment
- [ ] Configure rolling migration
- [ ] Configure canary deployment
- [ ] Configure feature flags

---

## Current Limitations

**Docker Desktop Not Running:**
- Cannot test deployment locally
- Cannot test rollback locally
- Cannot test migration locally
- Runtime verification blocked

**No CI/CD Infrastructure:**
- No GitHub Actions configured
- No staging environment
- No automated deployment
- No automated rollback

**No Secret Management:**
- Manual secret handling
- No secret rotation
- No audit logging

---

## References

- Docker Compose: `/Users/mohsenrassam/Desktop/Lumenly/.docker/docker-compose.yml`
- Backup scripts: `/Users/mohsenrassam/Desktop/Lumenly/backups/`
- Recovery runbooks: `/Users/mohsenrassam/Desktop/Lumenly/docs/runbooks/`
- Monitoring: `/Users/mohsenrassam/Desktop/Lumenly/monitoring/`

---

**Document Version:** 1.0
**Last Updated:** 2026-09-01
**Maintained By:** SRE Team
