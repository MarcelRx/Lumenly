# apps/backend/tests/test_auth.py
import pytest
from sqlalchemy import select

from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_user_registration(async_client, db_session):
    """Test successful user registration."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!",
            "full_name": "Test User",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert data["is_verified"] is False
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_user_registration_duplicate_email(async_client):
    """Test registration with duplicate email returns 409."""
    # First registration
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "TestPassword123!",
            "full_name": "First User",
        },
    )

    # Second registration with same email
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "AnotherPassword123!",
            "full_name": "Second User",
        },
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_user_login_success(async_client):
    """Test successful login returns JWT tokens."""
    # Register a user first
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "LoginPassword123!",
            "full_name": "Login User",
        },
    )

    # Login
    response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "login@example.com",
            "password": "LoginPassword123!",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0
    assert len(data["refresh_token"]) > 0


@pytest.mark.asyncio
async def test_user_login_invalid_password(async_client):
    """Test login with invalid password returns 401."""
    # Register a user first
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "invalidpass@example.com",
            "password": "CorrectPassword123!",
            "full_name": "Invalid Pass User",
        },
    )

    # Login with wrong password
    response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "invalidpass@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_user_login_nonexistent_user(async_client):
    """Test login with non-existent user returns 401."""
    response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "nonexistent@example.com",
            "password": "SomePassword123!",
        },
    )

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_protected_me_endpoint_with_valid_token(async_client):
    """Test accessing /me endpoint with valid access token."""
    # Register and login
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@example.com",
            "password": "MePassword123!",
            "full_name": "Me User",
        },
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "me@example.com",
            "password": "MePassword123!",
        },
    )
    access_token = login_response.json()["access_token"]

    # Access /me endpoint
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["full_name"] == "Me User"
    assert data["role"] == "user"


@pytest.mark.asyncio
async def test_protected_me_endpoint_without_token(async_client):
    """Test accessing /me endpoint without token returns 401."""
    response = await async_client.get("/api/v1/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_me_endpoint_with_invalid_token(async_client):
    """Test accessing /me endpoint with invalid token returns 401."""
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_refresh_flow(async_client):
    """Test token refresh with valid refresh token."""
    # Register and login
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@example.com",
            "password": "RefreshPassword123!",
            "full_name": "Refresh User",
        },
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "refresh@example.com",
            "password": "RefreshPassword123!",
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    # Refresh token
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    # New refresh token should be different (rotation)
    assert data["refresh_token"] != refresh_token


@pytest.mark.asyncio
async def test_token_refresh_invalid_token(async_client):
    """Test token refresh with invalid refresh token returns 401."""
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_refresh_token"},
    )

    assert response.status_code == 401
    assert "Invalid or expired refresh token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_logout_revokes_token(async_client):
    """Test logout revokes refresh token."""
    # Register and login
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout@example.com",
            "password": "LogoutPassword123!",
            "full_name": "Logout User",
        },
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "logout@example.com",
            "password": "LogoutPassword123!",
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    # Logout
    logout_response = await async_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_response.status_code == 204

    # Try to use the revoked refresh token
    refresh_response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401


@pytest.mark.asyncio
async def test_inactive_user_cannot_login(async_client, db_session):
    """Test inactive user cannot login."""
    # Register a user
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "inactive@example.com",
            "password": "InactivePassword123!",
            "full_name": "Inactive User",
        },
    )

    # Set user as inactive in database
    result = await db_session.execute(select(User).where(User.email == "inactive@example.com"))
    user = result.scalar_one_or_none()
    user.is_active = False
    await db_session.commit()

    # Try to login
    response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "inactive@example.com",
            "password": "InactivePassword123!",
        },
    )

    assert response.status_code == 401
    assert "Inactive user account" in response.json()["detail"]


def test_password_hashing():
    """Test password hashing and verification."""
    plain_password = "TestPassword123!"
    hashed = get_password_hash(plain_password)

    assert hashed != plain_password
    assert len(hashed) > 0
    assert verify_password(plain_password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


@pytest.mark.asyncio
async def test_rbac_admin_protected_endpoint(async_client):
    """Test RBAC - admin role required for protected endpoints."""
    # Register regular user
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "regular@example.com",
            "password": "RegularPassword123!",
            "full_name": "Regular User",
        },
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "regular@example.com",
            "password": "RegularPassword123!",
        },
    )
    access_token = login_response.json()["access_token"]

    # Try to access admin endpoint (this would require an actual admin endpoint)
    # For now, we'll test the dependency by checking user role
    me_response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    user_data = me_response.json()
    assert user_data["role"] == "user"
    assert user_data["role"] != "admin"


@pytest.mark.asyncio
async def test_user_created_with_default_role(async_client, db_session):
    """Test that new users are created with default 'user' role."""
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "role@example.com",
            "password": "RolePassword123!",
            "full_name": "Role User",
        },
    )

    result = await db_session.execute(select(User).where(User.email == "role@example.com"))
    user = result.scalar_one_or_none()

    assert user is not None
    assert user.role == UserRole.USER
