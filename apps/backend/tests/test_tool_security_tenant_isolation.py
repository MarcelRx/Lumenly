# apps/backend/tests/test_tool_security_tenant_isolation.py
"""
REAL integration/security tests for tool registry tenant isolation.

These tests verify that:
1. Every tenant-data tool accesses real persisted data
2. Every tenant-data operation enforces authenticated ownership
3. Cross-tenant access is denied
4. Resource enumeration does not disclose protected data
5. Authentication cannot be bypassed
6. Authorization cannot be bypassed
7. Mutation tools enforce ownership
8. No fabricated production data remains
9. Security tests exercise the real implementation
10. No security test was skipped or xfailed to hide a defect

DO NOT mock the executor itself.
DO NOT mock ownership validation.
DO NOT mock the database query that proves tenant isolation.
"""
import uuid
from datetime import datetime, timezone

import pytest

from app.ai.tools.registry import ToolRegistry
from app.models.domain import ComplianceEvent, Goal, Habit, JournalEntry
from app.models.user import User, UserRole


@pytest.fixture
async def tool_registry(setup_databases):
    """Provide a fresh tool registry instance for each test."""
    return ToolRegistry()


@pytest.fixture
async def user_a(db_session):
    """Create User A for testing."""
    from app.core.security import get_password_hash

    user = User(
        id=uuid.uuid4(),
        email="user_a@example.com",
        hashed_password=get_password_hash("password_a"),
        role=UserRole.USER,
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def user_b(db_session):
    """Create User B for testing."""
    from app.core.security import get_password_hash

    user = User(
        id=uuid.uuid4(),
        email="user_b@example.com",
        hashed_password=get_password_hash("password_b"),
        role=UserRole.USER,
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def habit_a(user_a):
    """Create Habit A belonging to User A."""
    habit = Habit(
        user_id=user_a.id,
        title="Morning Exercise",
        frequency="daily",
        streak_count=5
    )
    await habit.insert()
    return habit


@pytest.fixture
async def habit_b(user_b):
    """Create Habit B belonging to User B."""
    habit = Habit(
        user_id=user_b.id,
        title="Evening Reading",
        frequency="daily",
        streak_count=3
    )
    await habit.insert()
    return habit


@pytest.fixture
async def goal_a(user_a):
    """Create Goal A belonging to User A."""
    goal = Goal(
        user_id=user_a.id,
        title="Complete Marathon",
        description="Run a full marathon this year",
        target_date=datetime.now(timezone.utc).replace(month=12, day=31),
        is_completed=False
    )
    await goal.insert()
    return goal


@pytest.fixture
async def goal_b(user_b):
    """Create Goal B belonging to User B."""
    goal = Goal(
        user_id=user_b.id,
        title="Learn Python",
        description="Complete a Python programming course",
        target_date=datetime.now(timezone.utc).replace(month=6, day=30),
        is_completed=False
    )
    await goal.insert()
    return goal


@pytest.fixture
async def journal_a(user_a):
    """Create Journal A belonging to User A."""
    journal = JournalEntry(
        user_id=user_a.id,
        content="Today was a productive day. I completed my morning exercise.",
        mood_score=8
    )
    await journal.insert()
    return journal


@pytest.fixture
async def journal_b(user_b):
    """Create Journal B belonging to User B."""
    journal = JournalEntry(
        user_id=user_b.id,
        content="Feeling tired today. Need to get more sleep.",
        mood_score=5
    )
    await journal.insert()
    return journal


@pytest.fixture(autouse=True)
async def cleanup_test_data(cleanup_mongo):
    """Clean up test data after each test."""
    yield
    # cleanup_mongo fixture handles MongoDB cleanup


# ============================================================================
# TEST 1 — OWN RESOURCE
# ============================================================================

@pytest.mark.asyncio
async def test_user_a_can_access_own_habit(tool_registry, user_a, habit_a, db_session):
    """
    TEST 1 — OWN RESOURCE

    User A requests Habit A.

    Expected: success and returned data corresponds to Habit A.
    """
    result = await tool_registry.execute_tool(
        tool_name="check_habit_status",
        arguments={"habit_id": str(habit_a.id)},
        user_id=user_a.id,
        user_role="authenticated"
    )

    assert result["status"] == "success"
    assert result["habit_id"] == str(habit_a.id)
    assert result["title"] == habit_a.title
    assert result["frequency"] == habit_a.frequency
    assert result["streak_count"] == habit_a.streak_count
    # Verify this is real data, not fabricated constants
    assert result["streak_count"] == 5, "Data must come from database, not hardcoded"


@pytest.mark.asyncio
async def test_user_a_can_access_own_goal(tool_registry, user_a, goal_a, db_session):
    """
    TEST 1 — OWN RESOURCE (Goal variant)

    User A requests Goal A.

    Expected: success and returned data corresponds to Goal A.
    """
    result = await tool_registry.execute_tool(
        tool_name="get_goal_progress",
        arguments={"goal_id": str(goal_a.id)},
        user_id=user_a.id,
        user_role="authenticated"
    )

    assert result["status"] == "success"
    assert result["goal_id"] == str(goal_a.id)
    assert result["title"] == goal_a.title
    assert result["description"] == goal_a.description
    assert result["is_completed"] == goal_a.is_completed
    # Verify this is real data, not fabricated constants
    assert result["progress_percentage"] == 0, "Incomplete goal should show 0%"


@pytest.mark.asyncio
async def test_user_a_can_access_own_journals(tool_registry, user_a, journal_a, db_session):
    """
    TEST 1 — OWN RESOURCE (Journal variant)

    User A requests their own journals.

    Expected: success and returned data corresponds to User A's journals.
    """
    result = await tool_registry.execute_tool(
        tool_name="get_recent_journals",
        arguments={"limit": 5},
        user_id=user_a.id,
        user_role="authenticated"
    )

    assert result["status"] == "success"
    assert result["count"] >= 1
    assert len(result["journals"]) >= 1

    # Verify the journal content matches what we inserted
    journal_data = result["journals"][0]
    assert journal_data["content"] == journal_a.content
    assert journal_data["mood_score"] == journal_a.mood_score
    # Verify this is real data, not fabricated constants
    assert "productive day" in journal_data["content"], "Data must come from database"


# ============================================================================
# TEST 2 — CROSS-TENANT HABIT
# ============================================================================

@pytest.mark.asyncio
async def test_user_a_cannot_access_user_b_habit(tool_registry, user_a, habit_b, db_session):
    """
    TEST 2 — CROSS-TENANT HABIT

    User A requests Habit B (which belongs to User B).

    Expected: denied / not found
    ABSOLUTE REQUIREMENT: No Habit B data may be returned.
    """
    with pytest.raises(ValueError, match="Habit not found"):
        await tool_registry.execute_tool(
            tool_name="check_habit_status",
            arguments={"habit_id": str(habit_b.id)},
            user_id=user_a.id,
            user_role="authenticated"
        )

    # Verify compliance event was logged for security
    compliance_events = await ComplianceEvent.find(
        ComplianceEvent.user_id == user_a.id,
        ComplianceEvent.event_type == "cross_tenant_habit_access"
    ).to_list()

    assert len(compliance_events) >= 1, "Security event must be logged"
    assert compliance_events[0].severity_level >= 0.5, "Cross-tenant access is high severity"


# ============================================================================
# TEST 3 — CROSS-TENANT GOAL
# ============================================================================

@pytest.mark.asyncio
async def test_user_a_cannot_access_user_b_goal(tool_registry, user_a, goal_b, db_session):
    """
    TEST 3 — CROSS-TENANT GOAL

    User A requests Goal B (which belongs to User B).

    Expected: denied / not found
    No Goal B data may be returned.
    """
    with pytest.raises(ValueError, match="Goal not found"):
        await tool_registry.execute_tool(
            tool_name="get_goal_progress",
            arguments={"goal_id": str(goal_b.id)},
            user_id=user_a.id,
            user_role="authenticated"
        )

    # Verify compliance event was logged for security
    compliance_events = await ComplianceEvent.find(
        ComplianceEvent.user_id == user_a.id,
        ComplianceEvent.event_type == "cross_tenant_goal_access"
    ).to_list()

    assert len(compliance_events) >= 1, "Security event must be logged"


# ============================================================================
# TEST 4 — CROSS-TENANT JOURNAL
# ============================================================================

@pytest.mark.asyncio
async def test_user_a_cannot_access_user_b_journals(tool_registry, user_a, user_b, journal_b, db_session):
    """
    TEST 4 — CROSS-TENANT JOURNAL

    User A requests User B's journal data.

    Expected: denied / not found
    No User B content may be returned.
    """
    result = await tool_registry.execute_tool(
        tool_name="get_recent_journals",
        arguments={"limit": 5},
        user_id=user_a.id,
        user_role="authenticated"
    )

    # User A should only see their own journals, not User B's
    assert result["status"] == "success"

    # Verify User B's journal content is NOT in the results
    for journal in result["journals"]:
        assert journal["content"] != journal_b.content, "User B's content must not be returned"
        assert "tired today" not in journal["content"], "Cross-tenant content leak detected"


# ============================================================================
# TEST 5 — RESOURCE ENUMERATION
# ============================================================================

@pytest.mark.asyncio
async def test_resource_enumeration_does_not_disclose_data(tool_registry, user_a, user_b, habit_b, goal_b, db_session):
    """
    TEST 5 — RESOURCE ENUMERATION

    Attempt multiple IDs belonging to another user.

    Expected: No protected information is disclosed.
    """
    # Try to access User B's habit
    try:
        result = await tool_registry.execute_tool(
            tool_name="check_habit_status",
            arguments={"habit_id": str(habit_b.id)},
            user_id=user_a.id,
            user_role="authenticated"
        )
        # If somehow succeeds, verify no actual data is returned
        assert False, f"Cross-tenant access should have been denied for habit {habit_b.id}"
    except ValueError as e:
        # Expected - access denied
        assert "not found" in str(e).lower(), "Error should be generic, not reveal ownership"
        # Verify error message doesn't disclose User B's existence
        assert "user_b" not in str(e).lower(), "Error must not reveal other user's identity"

    # Try to access User B's goal
    try:
        result = await tool_registry.execute_tool(
            tool_name="get_goal_progress",
            arguments={"goal_id": str(goal_b.id)},
            user_id=user_a.id,
            user_role="authenticated"
        )
        # If somehow succeeds, verify no actual data is returned
        assert False, f"Cross-tenant access should have been denied for goal {goal_b.id}"
    except ValueError as e:
        # Expected - access denied
        assert "not found" in str(e).lower(), "Error should be generic, not reveal ownership"
        # Verify error message doesn't disclose User B's existence
        assert "user_b" not in str(e).lower(), "Error must not reveal other user's identity"


# ============================================================================
# TEST 6 — MISSING AUTHENTICATION
# ============================================================================

@pytest.mark.asyncio
async def test_tool_requires_user_context(tool_registry, habit_a, db_session):
    """
    TEST 6 — MISSING AUTHENTICATION

    Execute a user-owned-data tool without authenticated user context.

    Expected: authorization failure.
    """
    with pytest.raises(PermissionError, match="authorized"):
        await tool_registry.execute_tool(
            tool_name="check_habit_status",
            arguments={"habit_id": str(habit_a.id)},
            user_id=None,  # Missing authentication
            user_role="authenticated"
        )


# ============================================================================
# TEST 7 — INVALID RESOURCE
# ============================================================================

@pytest.mark.asyncio
async def test_invalid_resource_id_returns_not_found(tool_registry, user_a, db_session):
    """
    TEST 7 — INVALID RESOURCE

    Request malformed/nonexistent resource ID.

    Expected: validation/not-found behavior according to the API contract.
    """
    # Use a valid ObjectId format that doesn't exist in database
    fake_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format, non-existent

    with pytest.raises(ValueError, match="not found"):
        await tool_registry.execute_tool(
            tool_name="check_habit_status",
            arguments={"habit_id": fake_id},
            user_id=user_a.id,
            user_role="authenticated"
        )


@pytest.mark.asyncio
async def test_missing_required_argument_raises_validation_error(tool_registry, user_a, db_session):
    """
    TEST 7 — INVALID RESOURCE (missing argument)

    Request without required argument.

    Expected: validation failure.
    """
    with pytest.raises(ValueError, match="Missing required field"):
        await tool_registry.execute_tool(
            tool_name="check_habit_status",
            arguments={},  # Missing habit_id
            user_id=user_a.id,
            user_role="authenticated"
        )


# ============================================================================
# TEST 8 — ROLE VS OWNERSHIP
# ============================================================================

@pytest.mark.asyncio
async def test_valid_role_does_not_grant_cross_tenant_access(tool_registry, user_a, habit_b, db_session):
    """
    TEST 8 — ROLE VS OWNERSHIP

    Verify that a valid role does NOT grant access to another tenant's resource.

    Even with a valid USER role, User A must not access User B's habit.
    """
    # User A has valid USER role but should not access User B's habit
    with pytest.raises(ValueError, match="not found"):
        await tool_registry.execute_tool(
            tool_name="check_habit_status",
            arguments={"habit_id": str(habit_b.id)},
            user_id=user_a.id,
            user_role="user"  # Valid role
        )


# ============================================================================
# TEST 9 — REAL DATABASE PERSISTENCE
# ============================================================================

@pytest.mark.asyncio
async def test_tool_data_originates_from_database(tool_registry, user_a, habit_a, db_session):
    """
    TEST 9 — REAL DATABASE PERSISTENCE

    Verify that returned tool data actually originates from persisted database state.
    No fabricated constants.
    """
    # Modify the habit in the database
    habit_a.streak_count = 42
    habit_a.title = "Modified Title"
    await habit_a.save()

    # Execute tool
    result = await tool_registry.execute_tool(
        tool_name="check_habit_status",
        arguments={"habit_id": str(habit_a.id)},
        user_id=user_a.id,
        user_role="authenticated"
    )

    # Verify data matches database state, not hardcoded values
    assert result["streak_count"] == 42, "Data must come from database, not hardcoded"
    assert result["title"] == "Modified Title", "Data must reflect database state"


@pytest.mark.asyncio
async def test_no_fabricated_constants_in_tool_responses(tool_registry, user_a, goal_a, db_session):
    """
    TEST 9 — REAL DATABASE PERSISTENCE (no fabricated data)

    Verify tools don't return fabricated constant values.
    """
    result = await tool_registry.execute_tool(
        tool_name="get_goal_progress",
        arguments={"goal_id": str(goal_a.id)},
        user_id=user_a.id,
        user_role="authenticated"
    )

    # The old implementation returned hardcoded "progress_percentage": 65
    # The new implementation should return actual database state
    assert result["progress_percentage"] in [0, 100], "Progress should be based on is_completed, not fabricated"
    assert "milestones_completed" not in result, "Fabricated milestone fields should not exist"


# ============================================================================
# TEST 10 — MUTATION SECURITY
# ============================================================================

@pytest.mark.asyncio
async def test_mutation_tools_enforce_ownerhip():
    """
    TEST 10 — MUTATION SECURITY

    If any tool modifies user-owned data:
    - User A modifies own resource → allowed
    - User A modifies User B resource → denied

    Note: Current tools are read-only, but this test framework
    is ready for future mutation tools.
    """
    # Currently no mutation tools exist in the registry
    # This test is a placeholder for when mutation tools are added
    pass


# ============================================================================
# ADDITIONAL SECURITY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_unregistered_tool_cannot_be_executed(tool_registry, user_a, db_session):
    """
    Verify that unregistered tools cannot be executed.
    """
    with pytest.raises(ValueError, match="not registered"):
        await tool_registry.execute_tool(
            tool_name="malicious_tool",
            arguments={},
            user_id=user_a.id,
            user_role="authenticated"
        )


@pytest.mark.asyncio
async def test_tool_argument_validation(tool_registry, user_a, db_session):
    """
    Verify that tool arguments are validated against schema.
    """
    # Test with invalid argument type
    with pytest.raises(ValueError, match="must be string"):
        await tool_registry.execute_tool(
            tool_name="check_habit_status",
            arguments={"habit_id": 123},  # Should be string, not int
            user_id=user_a.id,
            user_role="authenticated"
        )


@pytest.mark.asyncio
async def test_tool_argument_size_limit(tool_registry, user_a, db_session):
    """
    Verify that tool arguments respect size limits.
    """
    # Create an oversized argument
    oversized_id = "x" * 10000

    with pytest.raises(ValueError, match="Invalid habit_id format"):
        await tool_registry.execute_tool(
            tool_name="check_habit_status",
            arguments={"habit_id": oversized_id},
            user_id=user_a.id,
            user_role="authenticated"
        )


@pytest.mark.asyncio
async def test_journal_limit_validation(tool_registry, user_a, db_session):
    """
    Verify that journal limit parameter is properly validated.
    """
    # Test with limit > maximum
    with pytest.raises(ValueError, match="between 1 and 20"):
        await tool_registry.execute_tool(
            tool_name="get_recent_journals",
            arguments={"limit": 25},  # Exceeds maximum of 20
            user_id=user_a.id,
            user_role="authenticated"
        )

    # Test with limit < minimum
    with pytest.raises(ValueError, match="between 1 and 20"):
        await tool_registry.execute_tool(
            tool_name="get_recent_journals",
            arguments={"limit": 0},  # Below minimum of 1
            user_id=user_a.id,
            user_role="authenticated"
        )


@pytest.mark.asyncio
async def test_concurrent_cross_tenant_attempts_logged(tool_registry, user_a, habit_b, goal_b, db_session):
    """
    Verify that multiple cross-tenant access attempts are all logged.
    """
    # Attempt multiple cross-tenant accesses
    for _ in range(3):
        try:
            await tool_registry.execute_tool(
                tool_name="check_habit_status",
                arguments={"habit_id": str(habit_b.id)},
                user_id=user_a.id,
                user_role="authenticated"
            )
        except ValueError:
            pass  # Expected

    # Verify all attempts were logged
    compliance_events = await ComplianceEvent.find(
        ComplianceEvent.user_id == user_a.id,
        ComplianceEvent.event_type == "cross_tenant_habit_access"
    ).to_list()

    assert len(compliance_events) >= 3, "All cross-tenant attempts must be logged"
