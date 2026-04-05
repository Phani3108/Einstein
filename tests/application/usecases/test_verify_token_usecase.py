"""Tests for VerifyTokenUseCase."""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.application.usecases.verify_token_usecase import VerifyTokenUseCase
from src.domain.entities.user import User
from src.domain.exceptions import InvalidTokenError
from src.domain.services.authentication_service import AuthenticationService, TokenData
from src.domain.services.user_management_service import UserManagementService


class TestVerifyTokenUseCase:
    """Test cases for VerifyTokenUseCase."""

    @pytest.fixture
    def mock_authentication_service(self):
        """Create a mock authentication service."""
        return Mock(spec=AuthenticationService)

    @pytest.fixture
    def mock_user_management_service(self):
        """Create a mock user management service."""
        return Mock(spec=UserManagementService)

    @pytest.fixture
    def verify_token_usecase(self, mock_authentication_service, mock_user_management_service):
        """Create a VerifyTokenUseCase instance with mocked dependencies."""
        return VerifyTokenUseCase(
            authentication_service=mock_authentication_service,
            user_management_service=mock_user_management_service,
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
    def sample_token_data(self, sample_user):
        """Create sample token data."""
        return TokenData(
            user_id=sample_user.id,
            email=sample_user.email,
            is_admin=sample_user.is_admin,
        )

    @pytest.mark.asyncio
    async def test_execute_successful_verification(
        self,
        verify_token_usecase,
        mock_authentication_service,
        mock_user_management_service,
        sample_user,
        sample_token_data,
    ):
        """Test successful token verification."""
        # Arrange
        token = "valid.jwt.token"
        mock_authentication_service.verify_token = AsyncMock(return_value=sample_token_data)
        mock_user_management_service.get_user_by_id = AsyncMock(return_value=sample_user)

        # Act
        result = await verify_token_usecase.execute(token)

        # Assert
        assert result == sample_user
        mock_authentication_service.verify_token.assert_called_once_with(token)
        mock_user_management_service.get_user_by_id.assert_called_once_with(sample_user.id)

    @pytest.mark.asyncio
    async def test_execute_invalid_token(
        self,
        verify_token_usecase,
        mock_authentication_service,
    ):
        """Test verification with invalid token."""
        # Arrange
        token = "invalid.jwt.token"
        mock_authentication_service.verify_token = AsyncMock(
            side_effect=InvalidTokenError("Invalid token")
        )

        # Act & Assert
        with pytest.raises(InvalidTokenError):
            await verify_token_usecase.execute(token)

    @pytest.mark.asyncio
    async def test_execute_user_not_found(
        self,
        verify_token_usecase,
        mock_authentication_service,
        mock_user_management_service,
        sample_token_data,
    ):
        """Test verification when user no longer exists."""
        # Arrange
        token = "valid.jwt.token"
        mock_authentication_service.verify_token = AsyncMock(return_value=sample_token_data)
        mock_user_management_service.get_user_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(InvalidTokenError, match="User associated with token no longer exists"):
            await verify_token_usecase.execute(token)

    @pytest.mark.asyncio
    async def test_execute_user_deactivated(
        self,
        verify_token_usecase,
        mock_authentication_service,
        mock_user_management_service,
        sample_user,
        sample_token_data,
    ):
        """Test verification when user is deactivated."""
        # Arrange
        token = "valid.jwt.token"
        deactivated_user = sample_user.model_copy(update={"is_active": False})
        
        mock_authentication_service.verify_token = AsyncMock(return_value=sample_token_data)
        mock_user_management_service.get_user_by_id = AsyncMock(return_value=deactivated_user)

        # Act & Assert
        with pytest.raises(InvalidTokenError, match="User account is deactivated"):
            await verify_token_usecase.execute(token)

    @pytest.mark.asyncio
    async def test_execute_admin_user(
        self,
        verify_token_usecase,
        mock_authentication_service,
        mock_user_management_service,
    ):
        """Test verification with admin user."""
        # Arrange
        token = "valid.jwt.token"
        admin_user = User(
            id=uuid4(),
            email="admin@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_admin=True,
        )
        admin_token_data = TokenData(
            user_id=admin_user.id,
            email=admin_user.email,
            is_admin=True,
        )

        mock_authentication_service.verify_token = AsyncMock(return_value=admin_token_data)
        mock_user_management_service.get_user_by_id = AsyncMock(return_value=admin_user)

        # Act
        result = await verify_token_usecase.execute(token)

        # Assert
        assert result == admin_user
        assert result.is_admin is True