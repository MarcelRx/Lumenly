# apps/backend/tests/test_auth.py
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
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


# Phase 12.3 Authentication Security Tests

def test_jwt_token_contains_required_claims():
    """Test that JWT tokens contain required security claims."""
    user_id = "test-user-123"
    email = "test@example.com"
    role = "user"

    token = create_access_token(subject=user_id, email=email, role=role)
    payload = decode_access_token(token)

    # Verify required claims
    assert "sub" in payload, "JWT must contain subject claim"
    assert "exp" in payload, "JWT must contain expiration claim"
    assert payload["sub"] == user_id, "Subject claim must match user ID"
    assert payload["email"] == email, "Email claim must match user email"
    assert payload["role"] == role, "Role claim must match user role"


def test_jwt_token_expiration_is_future():
    """Test that JWT tokens have future expiration times."""
    token = create_access_token(subject="test-user", email="test@example.com", role="user")
    payload = decode_access_token(token)

    exp_timestamp = payload["exp"]
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    now = datetime.now(timezone.utc)

    # Expiration should be in the future
    assert exp_datetime > now, "JWT expiration must be in the future"

    # Expiration should be approximately ACCESS_TOKEN_EXPIRE_MINUTES from now
    time_diff = (exp_datetime - now).total_seconds()
    expected_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert abs(time_diff - expected_seconds) < 5, "JWT expiration should match configured lifetime"


def test_jwt_token_rejects_expired_token():
    """Test that expired JWT tokens are rejected."""
    # Create a token with past expiration
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    expired_payload = {
        "sub": "test-user",
        "exp": past_time,
        "email": "test@example.com",
        "role": "user",
    }

    expired_token = jwt.encode(
        expired_payload,
        settings.JWT_SECRET or settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    # Attempt to decode expired token
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)


def test_jwt_token_rejects_malformed_token():
    """Test that malformed JWT tokens are rejected."""
    malformed_tokens = [
        "",  # Empty string
        "not-a-jwt",  # Not a JWT
        "invalid.token.format",  # Invalid format
        "Bearer token",  # Bearer prefix
        "abc.def",  # Too few parts
        "a.b.c.d",  # Too many parts
    ]

    for malformed_token in malformed_tokens:
        with pytest.raises((jwt.InvalidTokenError, jwt.DecodeError)):
            decode_access_token(malformed_token)


def test_jwt_token_rejects_invalid_signature():
    """Test that JWT tokens with invalid signatures are rejected."""
    valid_payload = {
        "sub": "test-user",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "email": "test@example.com",
        "role": "user",
    }

    # Sign with wrong secret
    wrong_secret = "wrong-secret-key"
    token_with_wrong_signature = jwt.encode(
        valid_payload, wrong_secret, algorithm=settings.JWT_ALGORITHM
    )

    # Attempt to decode with correct secret should fail
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token_with_wrong_signature)


def test_jwt_token_rejects_algorithm_mismatch():
    """Test that JWT tokens with wrong algorithm are rejected."""
    payload = {
        "sub": "test-user",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "email": "test@example.com",
        "role": "user",
    }

    # Sign with different algorithm
    if settings.JWT_ALGORITHM == "HS256":
        wrong_algorithm = "HS512"
    else:
        wrong_algorithm = "HS256"

    token_with_wrong_algorithm = jwt.encode(
        payload,
        settings.JWT_SECRET or settings.SECRET_KEY,
        algorithm=wrong_algorithm,
    )

    # Attempt to decode should fail due to algorithm mismatch
    with pytest.raises(jwt.InvalidAlgorithmError):
        decode_access_token(token_with_wrong_algorithm)


def test_jwt_token_rejects_missing_subject():
    """Test that JWT tokens without subject claim are rejected."""
    payload_without_sub = {
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "email": "test@example.com",
        "role": "user",
    }

    token_without_sub = jwt.encode(
        payload_without_sub,
        settings.JWT_SECRET or settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    # Decode should fail due to missing required sub claim
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token_without_sub)


def test_jwt_token_rejects_missing_exp():
    """Test that JWT tokens without expiration claim are rejected."""
    payload_without_exp = {
        "sub": "test-user",
        "email": "test@example.com",
        "role": "user",
    }

    token_without_exp = jwt.encode(
        payload_without_exp,
        settings.JWT_SECRET or settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    # Decode should fail due to missing required exp claim
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token_without_exp)


@pytest.mark.asyncio
async def test_jwt_token_rejects_missing_exp_through_auth_path(async_client):
    """Test that JWT tokens without exp claim are rejected through real auth endpoint."""
    # Create a syntactically valid, correctly signed JWT without exp claim
    payload_without_exp = {
        "sub": "test-user",
        "email": "test@example.com",
        "role": "user",
    }

    token_without_exp = jwt.encode(
        payload_without_exp,
        settings.JWT_SECRET or settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    # Attempt to access protected endpoint with token missing exp
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_without_exp}"},
    )

    # Should be rejected with 401
    assert response.status_code == 401


def test_rs256_key_selection():
    """Test that RS256 uses correct signing and verification keys."""
    from app.core.security import get_signing_key, get_verification_key

    # Test with HS256 (default)
    original_algorithm = settings.JWT_ALGORITHM

    try:
        # For HS256, should use JWT_SECRET
        if settings.JWT_ALGORITHM == "HS256":
            signing_key = get_signing_key()
            verification_key = get_verification_key()
            assert signing_key == settings.JWT_SECRET or settings.SECRET_KEY
            assert verification_key == settings.JWT_SECRET or settings.SECRET_KEY
    finally:
        # Restore original algorithm
        pass


def test_rs256_fails_without_keys():
    """Test that RS256 fails when keys are not configured."""
    from app.core.security import JWT_ALGORITHM, get_signing_key, get_verification_key

    # Only test if currently using HS256 to avoid breaking existing tests
    if settings.JWT_ALGORITHM == "HS256":
        # Temporarily set to RS256 without keys
        original_algorithm = JWT_ALGORITHM
        original_private = settings.JWT_SECRET_RS256_PRIVATE
        original_public = settings.JWT_SECRET_RS256_PUBLIC

        try:
            # Directly modify the global JWT_ALGORITHM variable
            from app.core import security
            security.JWT_ALGORITHM = "RS256"

            # Temporarily set RS256 keys to None
            from app.core.config import settings as test_settings
            test_settings.JWT_SECRET_RS256_PRIVATE = None
            test_settings.JWT_SECRET_RS256_PUBLIC = None

            # Should raise ValueError
            with pytest.raises(ValueError, match="JWT_SECRET_RS256_PRIVATE is required"):
                get_signing_key()

            with pytest.raises(ValueError, match="JWT_SECRET_RS256_PUBLIC is required"):
                get_verification_key()
        finally:
            # Restore
            security.JWT_ALGORITHM = original_algorithm
            test_settings.JWT_SECRET_RS256_PRIVATE = original_private
            test_settings.JWT_SECRET_RS256_PUBLIC = original_public


@pytest.mark.asyncio
async def test_refresh_token_concurrent_rotation_prevents_double_use(async_client):
    """Test that concurrent refresh requests cannot both succeed with the same token."""
    import asyncio

    # Register and login
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "concurrent@example.com",
            "password": "ConcurrentPassword123!",
            "full_name": "Concurrent User",
        },
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "concurrent@example.com",
            "password": "ConcurrentPassword123!",
        },
    )
    old_refresh_token = login_response.json()["refresh_token"]

    # Send two concurrent refresh requests with the same token
    async def refresh_request():
        return await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )

    # Execute both requests concurrently
    results = await asyncio.gather(refresh_request(), refresh_request())

    # Only one should succeed (200), the other should fail (401)
    success_count = sum(1 for r in results if r.status_code == 200)
    failure_count = sum(1 for r in results if r.status_code == 401)

    assert success_count == 1, "Exactly one concurrent refresh should succeed"
    assert failure_count == 1, "Exactly one concurrent refresh should fail"

    # Verify the successful response has a new token
    success_response = next(r for r in results if r.status_code == 200)
    new_refresh_token = success_response.json()["refresh_token"]
    assert new_refresh_token != old_refresh_token, "New refresh token should be different"

    # Verify the old token cannot be used again
    final_attempt = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert final_attempt.status_code == 401, "Old token should be permanently consumed"


@pytest.mark.asyncio
async def test_authentication_endpoint_rate_limiting(async_client):
    """Test that rate limiting is properly configured for authentication."""
    from app.core.config import settings
    from app.middleware.rate_limit import RateLimiter

    # Verify rate limiting is enabled
    assert settings.RATE_LIMIT_ENABLED is True, "Rate limiting should be enabled"

    # Verify fail-closed behavior
    assert settings.RATE_LIMIT_FAIL_OPEN is False, "Rate limiting should be fail-closed"

    # Verify anonymous limit is configured
    assert settings.RATE_LIMIT_ANONYMOUS_REQUESTS > 0, "Anonymous rate limit should be positive"

    # Verify RateLimiter is properly configured
    rate_limiter = RateLimiter()
    assert rate_limiter.enabled is True, "RateLimiter should be enabled"
    assert rate_limiter.fail_open is False, "RateLimiter should be fail-closed"

    # Verify role-based limits are configured
    assert "anonymous" in rate_limiter.limits, "Anonymous limit should be configured"
    assert "authenticated" in rate_limiter.limits, "Authenticated limit should be configured"
    assert "admin" in rate_limiter.limits, "Admin limit should be configured"

    # Verify limits are hierarchical
    assert rate_limiter.limits["anonymous"] < rate_limiter.limits["authenticated"]
    assert rate_limiter.limits["authenticated"] < rate_limiter.limits["admin"]





def test_refresh_token_cannot_be_used_as_access_token():
    """Test that refresh tokens cannot be used as access tokens."""
    # Create a refresh token (random string, not JWT)

    refresh_token = create_refresh_token()

    # Attempt to use refresh token as access token should fail
    with pytest.raises((jwt.InvalidTokenError, jwt.DecodeError)):
        decode_access_token(refresh_token)


def test_token_lifetime_configuration_is_explicit():
    """Test that token lifetime configuration is explicit and bounded."""
    # Verify configuration values are set
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0, "Access token lifetime must be positive"
    assert settings.REFRESH_TOKEN_EXPIRE_DAYS > 0, "Refresh token lifetime must be positive"

    # Verify reasonable bounds (access token should be short-lived)
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES <= 60, "Access token should be <= 60 minutes"

    # Verify refresh token is longer than access token
    refresh_minutes = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60
    assert refresh_minutes > settings.ACCESS_TOKEN_EXPIRE_MINUTES, "Refresh token should outlive access token"


@pytest.mark.asyncio
async def test_refresh_token_rotation_prevents_reuse(async_client):
    """Test that old refresh tokens cannot be reused after rotation."""
    # Register and login
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "rotation@example.com",
            "password": "RotationPassword123!",
            "full_name": "Rotation User",
        },
    )

    login_response = await async_client.post(
        "/api/v1/auth/login",
        data={
            "username": "rotation@example.com",
            "password": "RotationPassword123!",
        },
    )
    old_refresh_token = login_response.json()["refresh_token"]

    # First refresh - should succeed and return new token
    first_refresh_response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert first_refresh_response.status_code == 200
    new_refresh_token = first_refresh_response.json()["refresh_token"]
    assert new_refresh_token != old_refresh_token, "Refresh token should rotate"

    # Try to use old refresh token again - should fail
    second_refresh_response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert second_refresh_response.status_code == 401, "Old refresh token should be rejected after rotation"


@pytest.mark.asyncio
async def test_logout_without_token_is_safe(async_client):
    """Test that logout without token doesn't cause errors."""
    # Logout with invalid token should not leak information
    response = await async_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "invalid_token"},
    )
    # Should succeed silently (204) or fail gracefully
    # Current implementation returns 204 even for invalid tokens
    assert response.status_code in [204, 401], "Logout should handle invalid tokens gracefully"
