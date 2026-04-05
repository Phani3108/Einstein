"""Tests for DefaultUserManagementService."""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.domain.entities.user import User
from src.domain.exceptions import (
    AuthenticationError,
    UserAlreadyExistsError,
    UserManagementError,
    UserNotFoundError,
    UserRegistrationError,
)
from src.domain.repositories.user_repository import UserRepository
from src.domain.services.authentication_service import AuthenticationService
from src.infrastructure.services.user_management_service import (
    DefaultUserManagementService,
    UserRegistrationData,
)


class TestDefaultUserManagementService:
    """Test cases for DefaultUserManagementService."""

    @pytest.fixture
    def mock_user_repository(self):
        """Create a mock user repository."""
        return Mock(spec=UserRepository)

    @pytest.fixture
    def mock_auth_service(self):
        """Create a mock authentication service."""
        return Mock(spec=AuthenticationService)

    @pytest.fixture
    def user_management_service(self, mock_user_repository, mock_auth_service):
        """Create a DefaultUserManagementService instance with mocked dependencies."""
        return DefaultUserManagementService(
            user_repository=mock_user_repository,
            authentication_service=mock_auth_service,
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

    @pytest.fixture
    def registration_data(self):
        """Create sample registration data."""
        return UserRegistrationData(
            email="newuser@example.com",
            password="password123",
        )

    @pytest.mark.asyncio
    async def test_register_user_success(
        self,
        user_management_service,
        mock_user_repository,
        mock_auth_service,
        registration_data,
    ):
        """Test successful user registration."""
        # Arrange
        mock_user_repository.find_by_email = AsyncMock(return_value=None)
        mock_auth_service.hash_password = AsyncMock(return_value="hashed_password")
        mock_user_repository.save = AsyncMock(return_value=Mock(spec=User))

        # Act
        result = await user_management_service.register_user(registration_data)

        # Assert
        mock_user_repository.find_by_email.assert_called_once_with(registration_data.email)
        mock_auth_service.hash_password.assert_called_once_with(registration_data.password)
        mock_user_repository.save.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_register_user_already_exists(
        self,
        user_management_service,
        mock_user_repository,
        registration_data,
        sample_user,
    ):
        """Test user registration when user already exists."""
        # Arrange
        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)

        # Act & Assert
        with pytest.raises(UserAlreadyExistsError):
            await user_management_service.register_user(registration_data)

    @pytest.mark.asyncio
    async def test_register_user_repository_error(
        self,
        user_management_service,
        mock_user_repository,
        mock_auth_service,
        registration_data,
    ):
        """Test user registration with repository error."""
        # Arrange
        mock_user_repository.find_by_email = AsyncMock(return_value=None)
        mock_auth_service.hash_password = AsyncMock(return_value="hashed_password")
        mock_user_repository.save = AsyncMock(side_effect=Exception("Database error"))

        # Act & Assert
        with pytest.raises(UserRegistrationError):
            await user_management_service.register_user(registration_data)

    @pytest.mark.asyncio
    async def test_authenticate_user_success(
        self,
        user_management_service,
        mock_user_repository,
        mock_auth_service,
        sample_user,
    ):
        """Test successful user authentication."""
        # Arrange
        email = "test@example.com"
        password = "password123"
        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)
        mock_auth_service.verify_password = AsyncMock(return_value=True)

        # Act
        result = await user_management_service.authenticate_user(email, password)

        # Assert
        assert result == sample_user
        mock_user_repository.find_by_email.assert_called_once_with(email)
        mock_auth_service.verify_password.assert_called_once_with(
            password, sample_user.hashed_password
        )

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(
        self,
        user_management_service,
        mock_user_repository,
    ):
        """Test user authentication when user not found."""
        # Arrange
        email = "nonexistent@example.com"
        password = "password123"
        mock_user_repository.find_by_email = AsyncMock(return_value=None)

        # Act
        result = await user_management_service.authenticate_user(email, password)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(
        self,
        user_management_service,
        mock_user_repository,
        sample_user,
    ):
        """Test user authentication when user is inactive."""
        # Arrange
        email = "test@example.com"
        password = "password123"
        inactive_user = sample_user.model_copy(update={"is_active": False})
        mock_user_repository.find_by_email = AsyncMock(return_value=inactive_user)

        # Act
        result = await user_management_service.authenticate_user(email, password)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(
        self,
        user_management_service,
        mock_user_repository,
        mock_auth_service,
        sample_user,
    ):
        """Test user authentication with wrong password."""
        # Arrange
        email = "test@example.com"
        password = "wrong_password"
        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)
        mock_auth_service.verify_password = AsyncMock(return_value=False)

        # Act
        result = await user_management_service.authenticate_user(email, password)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(
        self,
        user_management_service,
        mock_user_repository,
        sample_user,
    ):
        """Test successful get user by ID."""
        # Arrange
        user_id = sample_user.id
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)

        # Act
        result = await user_management_service.get_user_by_id(user_id)

        # Assert
        assert result == sample_user
        mock_user_repository.find_by_id.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_get_user_by_email_success(
        self,
        user_management_service,
        mock_user_repository,
        sample_user,
    ):
        """Test successful get user by email."""
        # Arrange
        email = sample_user.email
        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)

        # Act
        result = await user_management_service.get_user_by_email(email)

        # Assert
        assert result == sample_user
        mock_user_repository.find_by_email.assert_called_once_with(email)

    @pytest.mark.asyncio
    async def test_update_last_login_success(
        self,
        user_management_service,
        mock_user_repository,
        sample_user,
    ):
        """Test successful last login update."""
        # Arrange
        user_id = sample_user.id
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)
        mock_user_repository.update = AsyncMock()

        # Act
        await user_management_service.update_last_login(user_id)

        # Assert
        mock_user_repository.find_by_id.assert_called_once_with(user_id)
        mock_user_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_last_login_user_not_found(
        self,
        user_management_service,
        mock_user_repository,
    ):
        """Test last login update when user not found."""
        # Arrange
        user_id = uuid4()
        mock_user_repository.find_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(UserNotFoundError):
            await user_management_service.update_last_login(user_id)

    @pytest.mark.asyncio
    async def test_deactivate_user_success(
        self,
        user_management_service,
        mock_user_repository,
        sample_user,
    ):
        """Test successful user deactivation."""
        # Arrange
        user_id = sample_user.id
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)
        mock_user_repository.update = AsyncMock()

        # Act
        await user_management_service.deactivate_user(user_id)

        # Assert
        mock_user_repository.find_by_id.assert_called_once_with(user_id)
        mock_user_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_user_success(
        self,
        user_management_service,
        mock_user_repository,
        sample_user,
    ):
        """Test successful user activation."""
        # Arrange
        user_id = sample_user.id
        inactive_user = sample_user.model_copy(update={"is_active": False})
        mock_user_repository.find_by_id = AsyncMock(return_value=inactive_user)
        mock_user_repository.update = AsyncMock()

        # Act
        await user_management_service.activate_user(user_id)

        # Assert
        mock_user_repository.find_by_id.assert_called_once_with(user_id)
        mock_user_repository.update.assert_called_once()