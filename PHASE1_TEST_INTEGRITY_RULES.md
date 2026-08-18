# PHASE 1: ABSOLUTE TEST INTEGRITY RULES

**Established:** 2026-08-18  
**Status:** ACTIVE

## ABSOLUTE PROHIBITIONS (NEVER DO)

1. **NEVER add skip to a failing test**
   - Skipping a failing test hides production defects
   - If a test fails, fix the root cause
   - Exception: Only for unavailable external infrastructure with documented reason

2. **NEVER convert a failing test into xfail**
   - xfail is for expected failures in known edge cases
   - Not for hiding implementation defects
   - Not for test infrastructure issues

3. **NEVER remove assertions**
   - Weakening assertions reduces test coverage
   - If an assertion is wrong, fix the test logic
   - If production behavior changed, update the assertion

4. **NEVER weaken expected values**
   - Changing "equals" to "contains" reduces precision
   - Changing specific error to generic error reduces security verification
   - Maintain exact expectations unless production behavior legitimately changed

5. **NEVER mock away the system under test**
   - Mocking the WebSocket endpoint defeats security testing
   - Mocking authentication bypasses security verification
   - Mocking rate limiting eliminates verification
   - Test the actual implementation, not a fake

6. **NEVER bypass authentication**
   - Tests must use real JWT tokens
   - Tests must verify token validation
   - Tests must verify authorization enforcement

7. **NEVER bypass rate limiting**
   - Tests must use real Redis
   - Tests must verify rate limit enforcement
   - Tests must verify fail-closed behavior

8. **NEVER disable tenant isolation**
   - Tests must create real separate users
   - Tests must verify cross-user data isolation
   - Tests must verify database-level filtering

9. **NEVER use mock LLM in production configuration**
   - Production tests must use real providers or fail clearly
   - Development tests can use mocks but must be explicit
   - Never silently fall back to mock in production

10. **NEVER catch exceptions merely to make tests pass**
    - Try/except to hide failures is unacceptable
    - Let exceptions propagate to show real issues
    - Only catch for expected error cases that should be tested

11. **NEVER modify production behavior solely to satisfy an incorrect test**
    - If a test is wrong, fix the test
    - If production behavior is wrong, fix production
    - Never make production worse to pass a bad test

## ALLOWED ACTIONS (MAY DO)

1. **Fix genuinely incorrect tests**
   - Test logic errors
   - Wrong assertions
   - Incorrect test data
   - Justification: Test was objectively wrong

2. **Fix broken fixtures**
   - Async/sync mismatches
   - Missing dependencies
   - Incorrect setup/teardown
   - Justification: Test infrastructure defect

3. **Add proper integration fixtures**
   - WebSocket test helpers
   - Multi-user test helpers
   - JWT token generation helpers
   - Justification: Missing test infrastructure

4. **Add test containers**
   - MongoDB test instances
   - Redis test instances
   - PostgreSQL test instances
   - Justification: Need isolated test environments

5. **Create deterministic test providers**
   - Mock providers with known behavior
   - Test doubles with predictable responses
   - Justification: Need predictable test behavior

6. **Add missing production implementation**
   - Complete placeholder functions
   - Add missing security checks
   - Implement missing validation
   - Justification: Production code incomplete

7. **Improve production error handling**
   - Add missing exception handling
   - Improve error messages
   - Add proper logging
   - Justification: Production code defect

8. **Fix incorrect API contracts**
   - Fix request/response schemas
   - Fix endpoint signatures
   - Fix error response formats
   - Justification: API contract violation

9. **Fix race conditions**
   - Add proper synchronization
   - Fix async operations
   - Fix concurrent access
   - Justification: Production code defect

10. **Fix actual architecture defects**
    - Fix security vulnerabilities
    - Fix tenant isolation issues
    - Fix data consistency problems
    - Justification: Production code defect

## TEST JUSTIFICATION REQUIREMENTS

Every test change must include:

1. **Root Cause Analysis**
   - Why was the test failing/skipped?
   - What is the actual defect (test vs production)?
   - Evidence supporting the diagnosis

2. **Change Justification**
   - Which allowed action is being taken?
   - Why is this the correct fix?
   - Alternative approaches considered

3. **Verification Plan**
   - How will we verify the fix works?
   - What regression tests are needed?
   - How will we prevent recurrence?

## CURRENT TEST INFRASTRUCTURE ISSUES

### Issue 1: Async/Sync Fixture Mismatch
**Problem:** WebSocket tests use sync `client` fixture but need async database operations  
**Root Cause:** Test fixture design doesn't match WebSocket async nature  
**Fix:** Create async WebSocket test infrastructure  
**Justification:** Test infrastructure defect

### Issue 2: Unawaited Coroutine Warnings
**Problem:** 6 RuntimeWarnings for unawaited AsyncSession operations  
**Root Cause:** Sync test methods calling async database methods without await  
**Fix:** Convert test methods to async or use proper async fixtures  
**Justification:** Test infrastructure defect

### Issue 3: Incorrect Pytest Marking
**Problem:** 26 sync tests marked with @pytest.mark.asyncio  
**Root Cause:** Copy-paste errors or global mark misapplication  
**Fix:** Remove incorrect marks from sync tests  
**Justification:** Test configuration error

### Issue 4: Manual Test Skip
**Problem:** test_ai_ask_endpoint manually skipped  
**Root Cause:** Unknown - no justification provided  
**Fix:** Investigate and fix or provide documented reason  
**Justification:** Unknown - requires investigation

## IMMEDIATE ACTION PLAN

### Step 1: Fix Test Infrastructure (Priority 1)
1. Create async WebSocket test client fixture
2. Create JWT token generation helper
3. Create multi-user test helpers
4. Create session creation helpers

### Step 2: Fix Critical Warnings (Priority 1)
1. Fix unawaited coroutine warnings in WebSocket tests
2. Remove incorrect pytest.mark.asyncio from sync tests
3. Investigate and fix/rejustify manual test skip

### Step 3: Remove Security Test Skips (Priority 0)
1. Remove all 13 skipped security tests
2. Implement proper async test infrastructure
3. Verify all security tests execute and pass

## VERIFICATION CRITERIA

Phase 1 is complete when:

1. ✅ All test infrastructure issues identified and documented
2. ✅ All prohibited actions clearly defined
3. ✅ All allowed actions clearly defined
4. ✅ Justification requirements established
5. ✅ Action plan for fixing infrastructure defined
6. ✅ No unjustified test modifications will be made

**STATUS:** RULES ESTABLISHED - READY FOR PHASE 2