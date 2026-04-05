"""Tests for RegisterUserUseCase."""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.application.usecases.register_user_usecase import RegisterUserUseCase
from src.domain.entities.user import User
from src.domain.exceptions import UserAlreadyExistsError, UserRegistrationError
from src.domain.services.user_management_service import UserManagementService


class TestRegisterUserUseCase:
    """Test cases for RegisterUserUseCase."""

    @pytest.fixture
    def mock_user_management_service(self):
        """Create a mock user management service."""
        return Mock(spec=UserManagementService)

    @pytest.fixture
    def register_usecase(self, mock_user_management_service):
        """Create a RegisterUserUseCase instance with mocked dependencies."""
        return RegisterUserUseCase(
            user_management_service=mock_user_management_service
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
    async def test_execute_successful_registration(
        self,
        register_usecase,
        mock_user_management_service,
        sample_user,
    ):
        """Test successful user registration."""
        # Arrange
        email = "test@example.com"
        password = "password123"
        mock_user_management_service.register_user = AsyncMock(return_value=sample_user)

        # Act
        result = await register_usecase.execute(email, password)

        # Assert
        assert result == sample_user
        mock_user_management_service.register_user.assert_called_once()
        
        # Check that registration data was created correctly
        call_args = mock_user_management_service.register_user.call_args[0][0]
        assert call_args.email == email.lower()
        assert call_args.password == password

    @pytest.mark.asyncio
    async def test_execute_email_normalization(
        self,
        register_usecase,
        mock_user_management_service,
        sample_user,
    ):
        """Test that email is normalized (lowercased and trimmed)."""
        # Arrange
        email = "  TEST@EXAMPLE.COM  "
        password = "password123"
        mock_user_management_service.register_user = AsyncMock(return_value=sample_user)

        # Act
        await register_usecase.execute(email, password)

        # Assert
        call_args = mock_user_management_service.register_user.call_args[0][0]
        assert call_args.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_execute_empty_email_error(
        self,
        register_usecase,
    ):
        """Test registration with empty email."""
        # Arrange
        email = ""
        password = "password123"

        # Act & Assert
        with pytest.raises(UserRegistrationError, match="Email is required"):
            await register_usecase.execute(email, password)

    @pytest.mark.asyncio
    async def test_execute_whitespace_email_error(
        self,
        register_usecase,
    ):
        """Test registration with whitespace-only email."""
        # Arrange
        email = "   "
        password = "password123"

        # Act & Assert
        with pytest.raises(UserRegistrationError, match="Email is required"):
            await register_usecase.execute(email, password)

    @pytest.mark.asyncio
    async def test_execute_short_password_error(
        self,
        register_usecase,
    ):
        """Test registration with password too short."""
        # Arrange
        email = "test@example.com"
        password = "short"

        # Act & Assert
        with pytest.raises(UserRegistrationError, match="Password must be at least 8 characters long"):
            await register_usecase.execute(email, password)

    @pytest.mark.asyncio
    async def test_execute_empty_password_error(
        self,
        register_usecase,
    ):
        """Test registration with empty password."""
        # Arrange
        email = "test@example.com"
        password = ""

        # Act & Assert
        with pytest.raises(UserRegistrationError, match="Password must be at least 8 characters long"):
            await register_usecase.execute(email, password)

    @pytest.mark.asyncio
    async def test_execute_user_already_exists_error(
        self,
        register_usecase,
        mock_user_management_service,
    ):
        """Test registration when user already exists."""
        # Arrange
        email = "test@example.com"
        password = "password123"
        mock_user_management_service.register_user = AsyncMock(
            side_effect=UserAlreadyExistsError(email)
        )

        # Act & Assert
        with pytest.raises(UserAlreadyExistsError):
            await register_usecase.execute(email, password)

    @pytest.mark.asyncio
    async def test_execute_registration_service_error(
        self,
        register_usecase,
        mock_user_management_service,
    ):
        """Test registration with service error."""
        # Arrange
        email = "test@example.com"
        password = "password123"
        mock_user_management_service.register_user = AsyncMock(
            side_effect=UserRegistrationError("Service error")
        )

        # Act & Assert
        with pytest.raises(UserRegistrationError):
            await register_usecase.execute(email, password)