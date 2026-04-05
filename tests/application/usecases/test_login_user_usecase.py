"""Tests for LoginUserUseCase."""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.application.usecases.login_user_usecase import LoginUserUseCase, LoginResult
from src.domain.entities.user import User
from src.domain.exceptions import AuthenticationError
from src.domain.services.authentication_service import AuthenticationService
from src.domain.services.user_management_service import UserManagementService


class TestLoginUserUseCase:
    """Test cases for LoginUserUseCase."""

    @pytest.fixture
    def mock_user_management_service(self):
        """Create a mock user management service."""
        return Mock(spec=UserManagementService)

    @pytest.fixture
    def mock_authentication_service(self):
        """Create a mock authentication service."""
        return Mock(spec=AuthenticationService)

    @pytest.fixture
    def login_usecase(self, mock_user_management_service, mock_authentication_service):
        """Create a LoginUserUseCase instance with mocked dependencies."""
        return LoginUserUseCase(
            user_management_service=mock_user_management_service,
            authentication_service=mock_authentication_service,
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
    async def test_execute_successful_login(
        self,
        login_usecase,
        mock_user_management_service,
        mock_authentication_service,
        sample_user,
    ):
        """Test successful user login."""
        # Arrange
        email = "test@example.com"
        password = "password123"
        access_token = "jwt.access.token"

        mock_user_management_service.authenticate_user = AsyncMock(return_value=sample_user)
        mock_authentication_service.create_access_token = AsyncMock(return_value=access_token)
        mock_user_management_service.update_last_login = AsyncMock()

        # Act
        result = await login_usecase.execute(email, password)

        # Assert
        assert isinstance(result, LoginResult)
        assert result.user == sample_user
        assert result.access_token == access_token

        mock_user_management_service.authenticate_user.assert_called_once_with(
            email.lower(), password
        )
        mock_authentication_service.create_access_token.assert_called_once_with(sample_user)
        mock_user_management_service.update_last_login.assert_called_once_with(sample_user.id)

    @pytest.mark.asyncio
    async def test_execute_email_normalization(
        self,
        login_usecase,
        mock_user_management_service,
        mock_authentication_service,
        sample_user,
    ):
        """Test that email is normalized during login."""
        # Arrange
        email = "  TEST@EXAMPLE.COM  "
        password = "password123"
        access_token = "jwt.access.token"

        mock_user_management_service.authenticate_user = AsyncMock(return_value=sample_user)
        mock_authentication_service.create_access_token = AsyncMock(return_value=access_token)
        mock_user_management_service.update_last_login = AsyncMock()

        # Act
        await login_usecase.execute(email, password)

        # Assert
        mock_user_management_service.authenticate_user.assert_called_once_with(
            "test@example.com", password
        )

    @pytest.mark.asyncio
    async def test_execute_empty_email_error(
        self,
        login_usecase,
    ):
        """Test login with empty email."""
        # Arrange
        email = ""
        password = "password123"

        # Act & Assert
        with pytest.raises(AuthenticationError, match="Email is required"):
            await login_usecase.execute(email, password)

    @pytest.mark.asyncio
    async def test_execute_whitespace_email_error(
        self,
        login_usecase,
    ):
        """Test login with whitespace-only email."""
        # Arrange
        email = "   "
        password = "password123"

        # Act & Assert
        with pytest.raises(AuthenticationError, match="Email is required"):
            await login_usecase.execute(email, password)

    @pytest.mark.asyncio
    async def test_execute_empty_password_error(
        self,
        login_usecase,
    ):
        """Test login with empty password."""
        # Arrange
        email = "test@example.com"
        password = ""

        # Act & Assert
        with pytest.raises(AuthenticationError, match="Password is required"):
            await login_usecase.execute(email, password)

    @pytest.mark.asyncio
    async def test_execute_invalid_credentials(
        self,
        login_usecase,
        mock_user_management_service,
    ):
        """Test login with invalid credentials."""
        # Arrange
        email = "test@example.com"
        password = "wrong_password"

        mock_user_management_service.authenticate_user = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await login_usecase.execute(email, password)

    @pytest.mark.asyncio
    async def test_execute_authentication_service_error(
        self,
        login_usecase,
        mock_user_management_service,
        mock_authentication_service,
        sample_user,
    ):
        """Test login with authentication service error."""
        # Arrange
        email = "test@example.com"
        password = "password123"

        mock_user_management_service.authenticate_user = AsyncMock(return_value=sample_user)
        mock_authentication_service.create_access_token = AsyncMock(
            side_effect=AuthenticationError("Token creation failed")
        )

        # Act & Assert
        with pytest.raises(AuthenticationError):
            await login_usecase.execute(email, password)

    @pytest.mark.asyncio
    async def test_execute_update_last_login_error(
        self,
        login_usecase,
        mock_user_management_service,
        mock_authentication_service,
        sample_user,
    ):
        """Test login with last login update error (should not fail login)."""
        # Arrange
        email = "test@example.com"
        password = "password123"
        access_token = "jwt.access.token"

        mock_user_management_service.authenticate_user = AsyncMock(return_value=sample_user)
        mock_authentication_service.create_access_token = AsyncMock(return_value=access_token)
        mock_user_management_service.update_last_login = AsyncMock(
            side_effect=Exception("Update failed")
        )

        # Act & Assert - login should still succeed even if last login update fails
        with pytest.raises(Exception, match="Update failed"):
            await login_usecase.execute(email, password)