# apps/backend/tests/test_domain.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_journal_entry(async_client: AsyncClient, cleanup_mongo) -> None:
    """Test creating a journal entry as an authenticated user."""
    # Register and login a user
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "journal@example.com",
            "password": "JournalPassword123!",
            "full_name": "Journal User",
        },
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "journal@example.com",
            "password": "JournalPassword123!",
        },
    )
    access_token = login_response.json()["access_token"]

    # Create a journal entry
    response = await async_client.post(
        "/api/v1/journals/",
        json={
            "content": "Today was a great day. I learned about vector databases.",
            "mood_score": 8,
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Today was a great day. I learned about vector databases."
    assert data["mood_score"] == 8
    assert "id" in data
    assert "user_id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_journal_entries(async_client: AsyncClient, cleanup_mongo) -> None:
    """Test listing journal entries for the authenticated user."""
    # Register and login a user
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "list@example.com",
            "password": "ListPassword123!",
            "full_name": "List User",
        },
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "list@example.com",
            "password": "ListPassword123!",
        },
    )
    access_token = login_response.json()["access_token"]

    # Create multiple journal entries
    await async_client.post(
        "/api/v1/journals/",
        json={
            "content": "First entry",
            "mood_score": 7,
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    await async_client.post(
        "/api/v1/journals/",
        json={
            "content": "Second entry",
            "mood_score": 9,
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    # List journal entries
    response = await async_client.get(
        "/api/v1/journals/",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 2
    assert entries[0]["content"] == "First entry"
    assert entries[1]["content"] == "Second entry"


@pytest.mark.asyncio
async def test_journal_entry_isolation(async_client: AsyncClient, cleanup_mongo) -> None:
    """Test that users can only see their own journal entries (multi-tenant isolation)."""
    # Register and login first user
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "user1@example.com",
            "password": "User1Password123!",
            "full_name": "User One",
        },
    )

    login_response_1 = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "user1@example.com",
            "password": "User1Password123!",
        },
    )
    access_token_1 = login_response_1.json()["access_token"]

    # Create journal entry for user 1
    await async_client.post(
        "/api/v1/journals/",
        json={
            "content": "User 1's private entry",
            "mood_score": 8,
        },
        headers={"Authorization": f"Bearer {access_token_1}"},
    )

    # Register and login second user
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "user2@example.com",
            "password": "User2Password123!",
            "full_name": "User Two",
        },
    )

    login_response_2 = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "user2@example.com",
            "password": "User2Password123!",
        },
    )
    access_token_2 = login_response_2.json()["access_token"]

    # Create journal entry for user 2
    await async_client.post(
        "/api/v1/journals/",
        json={
            "content": "User 2's private entry",
            "mood_score": 6,
        },
        headers={"Authorization": f"Bearer {access_token_2}"},
    )

    # User 2 should only see their own entry
    response = await async_client.get(
        "/api/v1/journals/",
        headers={"Authorization": f"Bearer {access_token_2}"},
    )

    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 1
    assert entries[0]["content"] == "User 2's private entry"
    assert "User 1's private entry" not in [e["content"] for e in entries]


@pytest.mark.asyncio
async def test_get_journal_entry_unauthorized(async_client: AsyncClient, cleanup_mongo) -> None:
    """Test that accessing journal entries without authentication returns 401."""
    response = await async_client.get("/api/v1/journals/")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_journal_entry_without_mood(async_client: AsyncClient, cleanup_mongo) -> None:
    """Test creating a journal entry without a mood score (optional field)."""
    # Register and login a user
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "nomood@example.com",
            "password": "NoMoodPassword123!",
            "full_name": "No Mood User",
        },
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "nomood@example.com",
            "password": "NoMoodPassword123!",
        },
    )
    access_token = login_response.json()["access_token"]

    # Create a journal entry without mood score
    response = await async_client.post(
        "/api/v1/journals/",
        json={
            "content": "Entry without mood score",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Entry without mood score"
    assert data["mood_score"] is None
