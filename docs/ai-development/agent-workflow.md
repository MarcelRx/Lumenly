# AI-Assisted Development Workflow

## Overview

This document defines the expected workflow for AI-assisted engineering in the Lumenly repository. The workflow ensures that AI agents produce verifiable, traceable, and safe changes while respecting architectural constraints and security requirements.

## Expected Workflow

### 1. Read Repository Instructions and Architecture Documents

**Before Starting:**
- Read this document (agent-workflow.md)
- Read the verification policy (verification-policy.md)
- Review relevant architecture documents:
  - `docs/architecture/system-architecture.md`
  - `docs/architecture/ai-architecture.md`
  - `docs/architecture/agent-orchestration.md`
  - `docs/architecture/data-flow.md`
- Review security documentation:
  - `docs/security/security-and-privacy.md`
- Review testing documentation:
  - `docs/engineering/testing-and-evaluation.md`

**Purpose:**
- Understand the codebase structure
- Understand architectural boundaries
- Understand security constraints
- Understand testing requirements

**Evidence:**
- Agent should reference specific architecture documents in its plan
- Agent should acknowledge security constraints

### 2. Identify the Assigned Issue or Task

**Task Identification:**
- Read the issue description or task requirements
- Identify acceptance criteria
- Identify related requirements (if any)
- Identify dependencies or blocking issues

**Questions to Answer:**
- What is the specific problem to solve?
- What are the acceptance criteria?
- What are the constraints?
- What are the risks?

**Evidence:**
- Agent should restate the task in its own words
- Agent should list acceptance criteria
- Agent should identify any ambiguities

### 3. Inspect Existing Implementation and Tests

**Code Inspection:**
- Locate relevant files using search tools
- Read existing implementation
- Read existing tests
- Understand current patterns and conventions
- Identify related components

**Test Inspection:**
- Locate relevant test files
- Understand test patterns
- Identify test coverage gaps
- Understand test data setup

**Evidence:**
- Agent should reference specific files read
- Agent should reference specific patterns identified
- Agent should note any test coverage gaps

### 4. Produce a Short Plan for Significant Changes

**Plan Requirements:**
- For significant changes (more than trivial edits), produce a plan
- Plan should include:
  - Files to be modified
  - New files to be created (if any)
  - Expected changes
  - Potential risks
  - Testing strategy
  - Rollback plan (if applicable)

**Plan Format:**
```
## Plan for [Task Name]

### Files to Modify
- `path/to/file1.py`: Reason for change
- `path/to/file2.py`: Reason for change

### New Files
- `path/to/new_file.py`: Purpose

### Expected Changes
- Change 1: Description
- Change 2: Description

### Potential Risks
- Risk 1: Description and mitigation
- Risk 2: Description and mitigation

### Testing Strategy
- Test 1: Description
- Test 2: Description

### Rollback Plan
- How to revert changes if needed
```

**When to Skip Planning:**
- Trivial fixes (typos, small refactors)
- Documentation updates
- Test additions without implementation changes

**Evidence:**
- Agent should produce plan before implementation
- Plan should be reviewed if requested

### 5. Identify Relevant Security and Architecture Constraints

**Security Constraints:**
- Never weaken existing security controls
- Never bypass rate limiting
- Never bypass authentication or authorization
- Never expose secrets or PII
- Never disable tenant isolation
- Never remove security tests

**Architecture Constraints:**
- Follow existing patterns and conventions
- Use existing libraries and utilities
- Respect component boundaries
- Maintain consistency with codebase style
- Add appropriate tests

**Specific Constraints:**
- Do not modify database schemas without migration
- Do not change API contracts without versioning
- Do not remove existing tests
- Do not break existing functionality

**Evidence:**
- Agent should list security constraints
- Agent should list architecture constraints
- Agent should explain how constraints will be respected

### 6. Implement the Smallest Appropriate Change

**Implementation Principles:**
- Make the smallest change that solves the problem
- Avoid large refactors unless explicitly required
- Avoid introducing new dependencies unless necessary
- Follow existing code style and patterns
- Add comments only when asked

**Implementation Steps:**
1. Make the change
2. Verify the change compiles/runs
3. Add or update tests
4. Run tests to verify

**Evidence:**
- Agent should describe the change made
- Agent should reference files modified
- Agent should explain why this is the smallest appropriate change

### 7. Add or Update Tests

**Test Requirements:**
- Add tests for new functionality
- Update tests for modified functionality
- Ensure tests pass
- Ensure tests are meaningful (not just coverage)

**Test Types:**
- Unit tests for individual functions
- Integration tests for component interactions
- Security tests for security-related changes
- API contract tests for API changes

**Test Evidence:**
- Agent should describe tests added
- Agent should show test results
- Agent should explain test coverage

### 8. Execute Relevant Verification Commands

**Verification Commands:**

**Run Tests:**
```bash
cd apps/backend
python -m pytest tests/ -v --tb=short --no-header
```

**Run Tests with Coverage:**
```bash
cd apps/backend
python -m pytest tests/ --cov=app --cov-report=xml --cov-report=term
```

**Run Lint:**
```bash
cd apps/backend
ruff check app/ --fix
ruff format app/
```

**Type Check (if applicable):**
```bash
cd apps/backend
mypy app/  # if mypy is configured
```

**Evidence:**
- Agent should show actual command output
- Agent should report exact results (passed, failed, warnings)
- Agent should not claim tests passed if not run

### 9. Inspect the Final Diff

**Diff Inspection:**
- Review all changes made
- Verify changes match the plan
- Verify no unintended changes
- Verify no secrets or PII exposed
- Verify security controls preserved

**Evidence:**
- Agent should show the diff
- Agent should explain each change
- Agent should confirm no unintended changes

### 10. Report Changed Files, Behavior, Test Results, Limitations, and Unresolved Risks

**Final Report Requirements:**

**Changed Files:**
- List all files modified
- List all files created
- List all files deleted (if any)

**Behavior Changes:**
- Describe what changed behaviorally
- Describe what stayed the same
- Describe any breaking changes

**Test Results:**
- Exact test command run
- Exact test results (passed, failed, skipped, xfailed)
- Total execution time
- Any warnings or errors

**Limitations:**
- What was not done
- What could not be verified
- What assumptions were made

**Unresolved Risks:**
- Any remaining risks
- Any areas needing further investigation
- Any areas needing human review

**Evidence:**
- Agent should provide complete final report
- Agent should not omit failures or warnings
- Agent should be honest about limitations

### 11. Associate Changes with Relevant Issue, Commit, or Pull Request

**Association:**
- Reference the issue number (if applicable)
- Reference the commit SHA (if committing)
- Reference the pull request (if creating PR)
- Link changes to acceptance criteria

**Evidence:**
- Agent should reference issue/commit/PR in final report
- Agent should explain how changes address acceptance criteria

### 12. Update Documentation When Implementation or Significant Decision Changes

**Documentation Updates:**
- Update architecture documents if architecture changes
- Update API documentation if API changes
- Update security documentation if security changes
- Update testing documentation if testing changes
- Update this document if workflow changes

**When to Update:**
- Architecture changes
- API contract changes
- Security control changes
- Testing approach changes
- Workflow changes

**Evidence:**
- Agent should list documentation updated
- Agent should explain why documentation needed update

## Escalation Requirements

### Destructive Operations

**Require Escalation:**
- Schema migrations (add/remove/modify database columns)
- Data deletion or truncation
- Configuration changes that affect security
- Breaking API changes
- Changes to authentication or authorization logic

**Escalation Process:**
1. Stop and describe the destructive operation
2. Explain why it's necessary
3. Propose a safe approach
4. Wait for human approval
5. Proceed only after approval

**Evidence:**
- Agent should identify destructive operations
- Agent should request approval before proceeding

### Schema Migrations

**Require Escalation:**
- Adding/removing/modifying database columns
- Adding/removing/modifying indexes
- Changing data types
- Migrating data

**Safe Approach:**
- Use Alembic for PostgreSQL migrations
- Use Beanie for MongoDB migrations (if needed)
- Test migrations in development first
- Have rollback plan ready

**Evidence:**
- Agent should use migration tools
- Agent should test migrations
- Agent should have rollback plan

### Security-Sensitive Changes

**Require Escalation:**
- Changes to authentication logic
- Changes to authorization logic
- Changes to rate limiting
- Changes to tenant isolation
- Changes to secret handling
- Changes to encryption

**Safe Approach:**
- Review security documentation
- Understand security implications
- Add security tests
- Request security review if unsure

**Evidence:**
- Agent should reference security documentation
- Agent should add security tests
- Agent should request review if unsure

### Credential Handling

**Require Escalation:**
- Adding new secrets
- Changing secret storage
- Exposing secrets in logs
- Removing secret validation

**Safe Approach:**
- Never log secrets
- Never commit secrets to Git
- Use environment variables
- Use secret management tools
- Validate secrets in production

**Evidence:**
- Agent should never log secrets
- Agent should never commit secrets
- Agent should use environment variables

### Changes with Broad Architectural Impact

**Require Escalation:**
- New major components
- Refactoring core architecture
- Changing data flow between components
- Adding new external dependencies
- Removing major components

**Safe Approach:**
- Review architecture documentation
- Understand architectural boundaries
- Propose ADR if needed
- Request architecture review

**Evidence:**
- Agent should reference architecture documentation
- Agent should propose ADR if needed
- Agent should request review if unsure

## Communication Requirements

### When to Ask Questions

**Ask Questions When:**
- Task description is ambiguous
- Acceptance criteria are unclear
- Security implications are uncertain
- Architectural impact is unclear
- Multiple approaches are possible
- Risk is identified but mitigation is unclear

**How to Ask:**
- State the ambiguity clearly
- Propose possible interpretations
- Explain the impact of each interpretation
- Recommend a path forward

**Evidence:**
- Agent should ask clarifying questions when needed
- Agent should not make assumptions about ambiguous tasks

### When to Propose Alternatives

**Propose Alternatives When:**
- Multiple valid approaches exist
- Trade-offs need to be evaluated
- Performance vs. simplicity trade-off
- Security vs. usability trade-off

**How to Propose:**
- Describe each alternative
- Explain pros and cons
- Recommend an approach with rationale
- Let human decide

**Evidence:**
- Agent should propose alternatives when appropriate
- Agent should explain trade-offs clearly

## Workflow Enforcement

### Self-Verification

**Before Completing:**
- Verify all tests pass
- Verify lint passes
- Verify diff is correct
- Verify no secrets exposed
- Verify documentation updated
- Verify final report complete

**Evidence:**
- Agent should perform self-verification
- Agent should report verification results

### Quality Gates

**Must Pass:**
- All relevant tests must pass
- Lint must pass (or warnings explained)
- No secrets exposed
- No security controls weakened
- No breaking changes without documentation

**Evidence:**
- Agent should report quality gate results
- Agent should not mark task complete if gates fail

## Agent Responsibilities

### Agent Must:**
- Follow this workflow
- Respect security and architecture constraints
- Ask questions when ambiguous
- Propose alternatives when appropriate
- Provide evidence for claims
- Report failures honestly
- Update documentation when needed
- Request escalation for destructive operations

### Agent Must Not:**
- Make assumptions about ambiguous tasks
- Bypass security controls
- Expose secrets or PII
- Remove existing tests
- Weaken security controls
- Claim tests passed without running
- Claim documentation reflects code without inspection
- Commit without approval (if not authorized)

## Human Responsibilities

### Human Must:**
- Provide clear task descriptions
- Provide clear acceptance criteria
- Review agent plans when requested
- Approve destructive operations
- Answer agent questions
- Review agent final reports
- Provide feedback on agent performance

### Human Must Not:**
- Expect agents to read minds
- Expect agents to work without context
- Assume agents understand implicit requirements
- Blame agents for following instructions
- Skip code review
- Ignore security warnings

## Continuous Improvement

### Workflow Updates

**When to Update:**
- If workflow is unclear
- If workflow is inefficient
- If workflow misses important steps
- If agents consistently fail at a step

**How to Update:**
- Propose change with rationale
- Get approval from team
- Update this document
- Communicate change to agents

**Evidence:**
- Document update history
- Explain rationale for changes

## Success Criteria

**Agent is Successful When:**
- Task is completed correctly
- Tests pass
- Security controls preserved
- Documentation updated
- Final report is complete and honest
- Human is satisfied with the result

**Human is Successful When:**
- Task description is clear
- Acceptance criteria are clear
- Questions are answered promptly
- Reviews are thorough
- Feedback is constructive
