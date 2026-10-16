# AI-Assisted Development Verification Policy

## Overview

This policy defines evidence-based acceptance criteria for AI-assisted engineering in the Lumenly repository. An AI agent's claim that work is complete must be supported by available evidence.

## Evidence-Based Acceptance Criteria

### Task Completion States

**Implemented:**
- Code changes have been made
- Changes are syntactically correct
- Changes compile or run without syntax errors

**Tested:**
- Tests have been added or updated
- Tests have been executed
- Test results are reported

**Independently Reviewed:**
- Code has been reviewed by a human
- Review comments have been addressed
- Review has been approved

**Merged:**
- Changes have been merged into the target branch
- Merge commit exists in Git history

**Deployed:**
- Changes have been deployed to an environment
- Deployment is verifiable (e.g., deployment record, environment URL)

**Verified in Target Environment:**
- Changes are running in the target environment
- Behavior is verified in the target environment
- Health checks pass in the target environment

**These states must not be treated as interchangeable.**

## Task-Level Reporting Requirements

### For Each Task, the Final Report Should Identify:

**Task or Issue Identifier:**
- Issue number (if applicable)
- Task description
- Acceptance criteria

**Intended Outcome:**
- What was supposed to be accomplished
- Expected behavior after changes

**Actual Changes:**
- Files modified (with paths)
- Files created (with paths)
- Files deleted (with paths, if any)
- Brief description of each change

**Relevant Commit or PR:**
- Commit SHA (if committed)
- Pull request number (if created)
- Link to commit or PR

**Tests and Checks Executed:**
- Exact test commands run
- Exact lint commands run
- Exact type check commands run (if applicable)
- Other verification commands run

**Exact Results:**
- Test results: passed, failed, skipped, xfailed counts
- Lint results: errors, warnings
- Type check results: errors, warnings
- Execution time (if available)
- Full output for failures

**Checks Not Executed and Why:**
- Which checks were not run
- Why they were not run (e.g., service unavailable, permission denied, not applicable)
- Whether they should be run later

**Security Implications:**
- Whether security controls were affected
- Whether new security risks were introduced
- Whether security tests were added/updated
- Whether security review is needed

**Known Limitations:**
- What was not done
- What could not be verified
- What assumptions were made
- What risks remain

**Remaining Work:**
- What still needs to be done
- What should be tracked as a separate task
- What requires human follow-up

**Deployment Evidence (if applicable):**
- Version or release identifier
- Commit SHA deployed
- CI or deployment workflow run
- Target environment
- Deployment outcome
- Relevant health checks or smoke tests
- Rollback procedure
- Unverified deployment assumptions

## Never Fabricate Evidence

### Do Not Claim:

**Reviewer:**
- Do not fabricate a reviewer
- Do not claim a review occurred without evidence
- Do not claim approval without evidence

**Approval:**
- Do not claim approval without evidence
- Do not claim CI passed without evidence
- Do not claim deployment succeeded without evidence

**CI Run:**
- Do not claim a CI workflow ran without evidence
- Do not claim CI passed without actual workflow evidence
- Do not fabricate CI run numbers or IDs

**Deployment:**
- Do not claim a deployment succeeded solely because a workflow file exists
- Do not claim a build passed because a Docker image was built
- Do not claim deployment to production without deployment evidence

**Test Results:**
- Do not claim tests passed if they were not run
- Do not fabricate test counts (passed, failed, skipped)
- Do not fabricate coverage percentages
- Do not fabricate execution times

**Lint Results:**
- Do not claim lint passes unless an actual lint command was executed successfully
- Do not claim type checking passes unless an actual type-check command was executed successfully

## Evidence Sources

### Authoritative Sources for Task Evidence

**Task-Level Detail:**
- GitHub Issues (task description, acceptance criteria)
- Pull Requests (discussion, review comments, approval)
- Issue or PR comments (decisions, unresolved concerns)

**Test Evidence:**
- CI workflow runs (GitHub Actions, GitLab CI, etc.)
- Local test execution (command output)
- Test reports (XML, JSON, HTML)
- Coverage reports (XML, JSON, HTML)

**Decision Evidence:**
- ADRs (Architecture Decision Records)
- Meeting notes (if available)
- Design documents (if available)
- Commit messages (rationale)

**Release and Deployment Evidence:**
- Release tags or releases in Git
- Deployment workflow runs
- Deployment logs
- Environment health checks
- Rollback records

**Actual Test Outcomes:**
- CI runs with specific run IDs
- Local test execution with specific command output
- Test reports with specific commit SHA
- Test reports with specific execution time

### Where to Store Evidence

**In Repository:**
- ADRs in `docs/decisions/`
- Test reports in repository (if committed)
- Deployment records in repository (if committed)

**In External Systems:**
- GitHub Issues and Pull Requests
- CI/CD system logs
- Deployment system logs
- Monitoring system dashboards

**In Agent Reports:**
- Final report should reference external evidence
- Final report should include local evidence (command output)
- Final report should link to external evidence when possible

## Distinguishing Historical from Current Evidence

### Historical Reports

**Labeling:**
- Historical reports should be labeled as historical
- Historical reports should include the commit SHA and date
- Historical reports should not be presented as current state

**Example:**
> "Phase 12.5 test results (historical): 832 passed, 1 xfailed at commit 4a93c03 on 2026-10-16"

**When to Use Historical Evidence:**
- When current verification is not possible
- When referencing past work
- When documenting evolution of the system

**When Not to Use Historical Evidence:**
- When claiming current state
- When claiming tests currently pass
- When claiming deployment currently works

### Current Evidence

**Requirements:**
- Must be verified against current code
- Must include commit SHA
- Must include execution date
- Must be reproducible

**When Current Evidence Differs:**
- Document the differences honestly
- Do not conceal failures
- Explain why results differ
- Recommend investigation

## Verification Commands

### Required Verification

**Always Run:**
- Relevant tests for the changes made
- Lint checks for the files modified
- Type checks (if configured)

**Commands:**

**Run Tests:**
```bash
cd apps/backend
python -m pytest tests/ -v --tb=short --no-header
```

**Run Specific Tests:**
```bash
cd apps/backend
python -m pytest tests/test_specific.py -v
```

**Run Lint:**
```bash
cd apps/backend
ruff check app/ --fix
ruff format app/
```

**Run Type Check (if applicable):**
```bash
cd apps/backend
mypy app/
```

### Optional Verification

**Run When Appropriate:**
- Coverage reports
- Integration tests
- End-to-end tests
- Security scans
- Performance tests

**Commands:**

**Run Coverage:**
```bash
cd apps/backend
python -m pytest tests/ --cov=app --cov-report=xml --cov-report=term
```

**Run Security Scan:**
```bash
trufflehog --only-verified ./
```

## Reporting Failures

### How to Report Failures

**Be Honest:**
- Report all failures
- Do not hide failures
- Do not downplay failures
- Do not claim "mostly passing" if there are failures

**Provide Context:**
- What command was run
- What the expected result was
- What the actual result was
- Full error output (if available)

**Investigate Failures:**
- Try to understand why failure occurred
- Propose possible causes
- Propose possible fixes
- Request human review if unsure

**Example Failure Report:**
```
Test Results:
Command: python -m pytest tests/test_auth.py -v
Result: 3 passed, 2 failed
Failures:
1. test_login_rate_limiting - AssertionError: Expected 429, got 200
2. test_token_rotation - TimeoutError: Token refresh timed out

Investigation:
- test_login_rate_limiting: Rate limiting may not be enabled in test environment
- test_token_rotation: Redis may be unavailable

Recommendation:
- Investigate rate limiting configuration
- Check Redis connectivity
- Request human review
```

## Reporting Warnings

### How to Report Warnings

**Report All Warnings:**
- Report lint warnings
- Report deprecation warnings
- Report security warnings
- Report any non-critical issues

**Classify Warnings:**
- Critical: Must be fixed
- Important: Should be fixed
- Cosmetic: Can be deferred
- External: Cannot fix (third-party)

**Example Warning Report:**
```
Lint Results:
Command: ruff check app/
Result: 0 errors, 15 warnings

Warnings:
- 5 unused variable warnings (cosmetic)
- 8 deprecation warnings (external - PyPDF2)
- 2 security warnings (test-only JWT key length)

Classification:
- Unused variables: Cosmetic, can be deferred
- Deprecation warnings: External, cannot fix in this codebase
- Security warnings: Test-only, not production concern
```

## Reporting Untested Areas

### How to Report Untested Areas

**Identify Gaps:**
- What functionality was added but not tested
- What functionality was modified but tests not updated
- What areas could not be tested due to limitations

**Explain Why:**
- Why tests were not added (e.g., time, complexity, dependency unavailable)
- Why tests could not be run (e.g., service unavailable, permission denied)
- What would be needed to test (e.g., specific environment, credentials)

**Recommend Next Steps:**
- What tests should be added later
- What verification should be done later
- What assumptions need to be validated

**Example Untested Area Report:**
```
Untested Areas:
- Voice pipeline: Not implemented, therefore not tested
- Production deployment: No production environment available
- Multi-region failover: No multi-region deployment

Recommendations:
- Add voice pipeline tests when implemented
- Verify deployment when production environment available
- Add failover tests when multi-region deployment configured
```

## Reporting Access Limitations

### How to Report Access Limitations

**Identify Limitations:**
- What services were unavailable
- What credentials were missing
- What permissions were missing
- What environments were inaccessible

**Explain Impact:**
- How limitation affected verification
- What could not be verified due to limitation
- What assumptions had to be made

**Recommend Workarounds:**
- How to work around limitation
- What would be needed to remove limitation
- What risks are introduced by limitation

**Example Access Limitation Report:**
```
Access Limitations:
- Production environment: No access
- Production database: No credentials
- External API keys: Not available

Impact:
- Could not verify production deployment
- Could not test with production data
- Could not test with real AI providers

Assumptions:
- Assuming Docker configuration matches production
- Assuming mock provider behavior matches real provider
- Assuming test environment is representative

Recommendations:
- Obtain production access for verification
- Test with real AI providers when credentials available
- Add integration tests with real services
```

## Reporting Deployment Evidence

### What to Report

**If Deployment Occurred:**
- Version or release identifier
- Commit SHA deployed
- CI or deployment workflow run ID
- Target environment (staging, production)
- Deployment outcome (success, failure, partial)
- Health check results after deployment
- Smoke test results (if run)
- Rollback procedure (if applicable)
- Any deployment issues encountered

**If Deployment Did Not Occur:**
- Explicitly state deployment did not occur
- Explain why deployment did not occur
- State what would be needed for deployment
- State what assumptions are being made about deployment

**Example Deployment Report:**
```
Deployment Evidence:
- No deployment occurred
- CI workflow ran: test, lint, security scan, build
- Docker image built: lumenly-backend:4a93c03
- Image not deployed to any environment

Assumptions:
- Assuming Docker image would run correctly in production
- Assuming environment variables would be configured correctly
- Assuming services would be available

What Would Be Needed:
- Kubernetes deployment configuration
- Environment-specific secrets
- Service mesh configuration
- Monitoring and alerting setup
```

## Verification Checklist

### Before Marking Task Complete

**Code Changes:**
- [ ] Changes implemented correctly
- [ ] Changes follow existing patterns
- [ ] Changes are minimal and focused
- [ ] No unintended changes
- [ ] No secrets or PII exposed

**Tests:**
- [ ] Tests added for new functionality
- [ ] Tests updated for modified functionality
- [ ] Tests executed successfully
- [ ] Test results reported accurately
- [ ] No unreported failures

**Lint:**
- [ ] Lint executed
- [ ] Lint results reported accurately
- [ ] No unreported errors
- [ ] Warnings explained or addressed

**Security:**
- [ ] Security controls preserved
- [ ] No new security risks introduced
- [ ] Security tests added if needed
- [ ] Security review requested if needed

**Documentation:**
- [ ] Architecture docs updated if needed
- [ ] API docs updated if needed
- [ ] Security docs updated if needed
- [ ] This workflow followed

**Final Report:**
- [ ] Changed files listed
- [ ] Behavior changes described
- [ ] Test results reported
- [ ] Limitations acknowledged
- [ ] Risks identified
- [ ] Deployment evidence or lack thereof reported

## Quality Standards

### What Constitutes Complete Work

**Complete Work:**
- All acceptance criteria met
- All tests passing
- All lint checks passing
- Security controls preserved
- Documentation updated
- Final report complete and honest

**Incomplete Work:**
- Acceptance criteria not met
- Tests failing
- Lint errors
- Security controls weakened
- Documentation not updated
- Final report missing or incomplete

**Unknown Work:**
- Cannot verify due to access limitations
- Cannot verify due to service unavailability
- Cannot verify due to missing dependencies
- Must report as unknown, not complete

## Consequences of Violating Policy

### For Agents

**If Agent Fabricates Evidence:**
- Report should be rejected
- Work should be re-reviewed
- Agent workflow should be audited
- Human should provide feedback

**If Agent Hides Failures:**
- Report should be rejected
- Work should be re-tested
- Agent should be retrained
- Human should provide feedback

**If Agent Makes Assumptions Without Stating Them:**
- Report should be questioned
- Assumptions should be validated
- Agent should be reminded to state assumptions
- Human should provide feedback

### For Humans

**If Human Ignores Agent Warnings:**
- Risk accepted by human
- Document acceptance of risk
- Follow up on risk later

**If Human Approves Without Review:**
- Risk accepted by human
- Document approval without review
- Consider requiring review in future

## Continuous Improvement

### Policy Updates

**When to Update:**
- If policy is unclear
- If policy is insufficient
- If agents consistently violate policy
- If humans provide feedback on policy

**How to Update:**
- Propose change with rationale
- Get approval from team
- Update this document
- Communicate change to agents and humans

## Summary

**Key Principles:**
1. Evidence is required for all claims
2. Do not fabricate evidence
3. Report failures honestly
4. Report limitations honestly
5. Distinguish historical from current evidence
6. Do not treat different states as interchangeable
7. Provide complete final reports
8. Ask for help when uncertain

**Evidence Sources:**
- GitHub Issues and Pull Requests
- CI/CD workflow runs
- Test reports
- Deployment records
- ADRs
- Commit messages

**Quality Gates:**
- Tests must pass
- Lint must pass
- Security controls must be preserved
- Documentation must be updated
- Final report must be complete

**Escalation:**
- Ask for help when uncertain
- Request review for destructive operations
- Request review for security-sensitive changes
- Request review for architectural changes
