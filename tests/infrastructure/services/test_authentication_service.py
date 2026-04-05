"""Tests for JWTAuthenticationService."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.domain.entities.user import User
from src.domain.exceptions import AuthenticationError, InvalidTokenError
from src.infrastructure.services.authentication_service import JWTAuthenticationService


class TestJWTAuthenticationService:
    """Test cases for JWTAuthenticationService."""

    @pytest.fixture
    def auth_service(self):
        """Create a JWTAuthenticationService instance for testing."""
        return JWTAuthenticationService(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=60,
        )

    @pytest.fixture
    def sample_user(self):
        """Create a sample user for testing."""
        return User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_admin=False,
        )

    @pytest.mark.asyncio
    async def test_hash_password(self, auth_service):
        """Test password hashing."""
        password = "test_password_123"
        
        hashed = await auth_service.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash format

    @pytest.mark.asyncio
    async def test_verify_password_correct(self, auth_service):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = await auth_service.hash_password(password)
        
        is_valid = await auth_service.verify_password(password, hashed)
        
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_password_incorrect(self, auth_service):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = await auth_service.hash_password(password)
        
        is_valid = await auth_service.verify_password(wrong_password, hashed)
        
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_create_access_token(self, auth_service, sample_user):
        """Test access token creation."""
        token = await auth_service.create_access_token(sample_user)
        
        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count(".") == 2  # JWT has 3 parts separated by dots

    @pytest.mark.asyncio
    async def test_create_access_token_with_custom_expiry(self, auth_service, sample_user):
        """Test access token creation with custom expiry."""
        custom_expiry = timedelta(minutes=30)
        
        token = await auth_service.create_access_token(sample_user, custom_expiry)
        
        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_verify_token_valid(self, auth_service, sample_user):
        """Test token verification with valid token."""
        token = await auth_service.create_access_token(sample_user)
        
        token_data = await auth_service.verify_token(token)
        
        assert token_data.user_id == sample_user.id
        assert token_data.email == sample_user.email
        assert token_data.is_admin == sample_user.is_admin
        assert token_data.expires_at is not None

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self, auth_service):
        """Test token verification with invalid token."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(InvalidTokenError):
            await auth_service.verify_token(invalid_token)

    @pytest.mark.asyncio
    async def test_verify_token_expired(self, auth_service, sample_user):
        """Test token verification with expired token."""
        # Create token with very short expiry
        expired_token = await auth_service.create_access_token(
            sample_user, timedelta(seconds=-1)  # Already expired
        )
        
        with pytest.raises(InvalidTokenError):
            await auth_service.verify_token(expired_token)

    @pytest.mark.asyncio
    async def test_refresh_token_valid(self, auth_service, sample_user):
        """Test token refresh with valid token."""
        original_token = await auth_service.create_access_token(sample_user)
        
        new_token = await auth_service.refresh_token(original_token)
        
        assert isinstance(new_token, str)
        assert new_token != original_token
        
        # Verify new token is valid
        token_data = await auth_service.verify_token(new_token)
        assert token_data.user_id == sample_user.id

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, auth_service):
        """Test token refresh with invalid token."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(InvalidTokenError):
            await auth_service.refresh_token(invalid_token)

    @pytest.mark.asyncio
    async def test_admin_user_token(self, auth_service):
        """Test token creation and verification for admin user."""
        admin_user = User(
            id=uuid4(),
            email="admin@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_admin=True,
        )
        
        token = await auth_service.create_access_token(admin_user)
        token_data = await auth_service.verify_token(token)
        
        assert token_data.is_admin is True

    def test_from_environment_missing_secret(self, monkeypatch):
        """Test creating service from environment with missing secret key."""
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        
        with pytest.raises(AuthenticationError, match="JWT_SECRET_KEY environment variable is required"):
            JWTAuthenticationService.from_environment()

    def test_from_environment_success(self, monkeypatch):
        """Test creating service from environment variables."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
        monkeypatch.setenv("JWT_ALGORITHM", "HS256")
        monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "120")
        
        service = JWTAuthenticationService.from_environment()
        
        assert service._secret_key == "test-secret"
        assert service._algorithm == "HS256"
        assert service._access_token_expire_minutes == 120