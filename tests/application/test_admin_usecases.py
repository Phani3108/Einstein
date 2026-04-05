"""Unit tests for admin use cases."""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from datetime import datetime

from src.application.usecases.get_users_usecase import GetUsersUseCase
from src.application.usecases.create_user_usecase import CreateUserUseCase
from src.application.usecases.get_system_health_usecase import GetSystemHealthUseCase
from src.domain.entities.user import User
from src.domain.exceptions import UserAlreadyExistsError


class TestGetUsersUseCase:
    """Test the GetUsersUseCase."""

    @pytest.fixture
    def mock_user_repository(self):
        """Create a mock user repository."""
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_user_repository):
        """Create the use case with mocked dependencies."""
        return GetUsersUseCase(mock_user_repository)

    async def test_execute_returns_users_list(self, use_case, mock_user_repository):
        """Test that execute returns a list of users."""
        # Arrange
        expected_users = [
            User(
                id=uuid4(),
                email="user1@example.com",
                hashed_password="hash1",
                is_admin=False,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            User(
                id=uuid4(),
                email="user2@example.com",
                hashed_password="hash2",
                is_admin=True,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]
        mock_user_repository.find_all.return_value = expected_users

        # Act
        result = await use_case.execute(skip=0, limit=10)

        # Assert
        assert result == expected_users
        mock_user_repository.find_all.assert_called_once_with(skip=0, limit=10)

    async def test_execute_with_custom_pagination(self, use_case, mock_user_repository):
        """Test execute with custom pagination parameters."""
        # Arrange
        mock_user_repository.find_all.return_value = []

        # Act
        await use_case.execute(skip=20, limit=50)

        # Assert
        mock_user_repository.find_all.assert_called_once_with(skip=20, limit=50)

    async def test_execute_with_default_pagination(self, use_case, mock_user_repository):
        """Test execute with default pagination parameters."""
        # Arrange
        mock_user_repository.find_all.return_value = []

        # Act
        await use_case.execute()

        # Assert
        mock_user_repository.find_all.assert_called_once_with(skip=0, limit=100)


class TestCreateUserUseCase:
    """Test the CreateUserUseCase."""

    @pytest.fixture
    def mock_user_repository(self):
        """Create a mock user repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_authentication_service(self):
        """Create a mock authentication service."""
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_user_repository, mock_authentication_service):
        """Create the use case with mocked dependencies."""
        return CreateUserUseCase(mock_user_repository, mock_authentication_service)

    async def test_execute_creates_user_successfully(
        self, use_case, mock_user_repository, mock_authentication_service
    ):
        """Test successful user creation."""
        # Arrange
        email = "newuser@example.com"
        password = "secure_password123"
        hashed_password = "hashed_secure_password123"

        mock_user_repository.find_by_email.return_value = None  # User doesn't exist
        mock_authentication_service.hash_password.return_value = hashed_password

        created_user = User(
            id=uuid4(),
            email=email,
            hashed_password=hashed_password,
            is_admin=False,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_user_repository.save.return_value = created_user

        # Act
        result = await use_case.execute(
            email=email, password=password, is_admin=False, is_active=True
        )

        # Assert
        assert result == created_user
        mock_user_repository.find_by_email.assert_called_once_with(email)
        mock_authentication_service.hash_password.assert_called_once_with(password)
        mock_user_repository.save.assert_called_once()

        # Verify the user object passed to save has correct properties
        saved_user = mock_user_repository.save.call_args[0][0]
        assert saved_user.email == email
        assert saved_user.hashed_password == hashed_password
        assert saved_user.is_admin is False
        assert saved_user.is_active is True

    async def test_execute_creates_admin_user(
        self, use_case, mock_user_repository, mock_authentication_service
    ):
        """Test creating an admin user."""
        # Arrange
        email = "admin@example.com"
        password = "admin_password123"
        hashed_password = "hashed_admin_password123"

        mock_user_repository.find_by_email.return_value = None
        mock_authentication_service.hash_password.return_value = hashed_password

        created_user = User(
            id=uuid4(),
            email=email,
            hashed_password=hashed_password,
            is_admin=True,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_user_repository.save.return_value = created_user

        # Act
        result = await use_case.execute(
            email=email, password=password, is_admin=True, is_active=True
        )

        # Assert
        saved_user = mock_user_repository.save.call_args[0][0]
        assert saved_user.is_admin is True

    async def test_execute_raises_error_when_user_exists(
        self, use_case, mock_user_repository, mock_authentication_service
    ):
        """Test that UserAlreadyExistsError is raised when user exists."""
        # Arrange
        email = "existing@example.com"
        existing_user = User(
            id=uuid4(),
            email=email,
            hashed_password="existing_hash",
            is_admin=False,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_user_repository.find_by_email.return_value = existing_user

        # Act & Assert
        with pytest.raises(UserAlreadyExistsError) as exc_info:
            await use_case.execute(
                email=email, password="password", is_admin=False, is_active=True
            )

        assert str(exc_info.value) == f"User with email {email} already exists"
        mock_user_repository.find_by_email.assert_called_once_with(email)
        mock_authentication_service.hash_password.assert_not_called()
        mock_user_repository.save.assert_not_called()

    async def test_execute_creates_inactive_user(
        self, use_case, mock_user_repository, mock_authentication_service
    ):
        """Test creating an inactive user."""
        # Arrange
        email = "inactive@example.com"
        password = "password123"
        hashed_password = "hashed_password123"

        mock_user_repository.find_by_email.return_value = None
        mock_authentication_service.hash_password.return_value = hashed_password

        created_user = User(
            id=uuid4(),
            email=email,
            hashed_password=hashed_password,
            is_admin=False,
            is_active=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_user_repository.save.return_value = created_user

        # Act
        result = await use_case.execute(
            email=email, password=password, is_admin=False, is_active=False
        )

        # Assert
        saved_user = mock_user_repository.save.call_args[0][0]
        assert saved_user.is_active is False


class TestGetSystemHealthUseCase:
    """Test the GetSystemHealthUseCase."""

    @pytest.fixture
    def mock_database(self):
        """Create a mock database."""
        mock_db = Mock()
        mock_session = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_db.session.return_value = mock_context_manager
        return mock_db

    @pytest.fixture
    def mock_user_repository(self):
        """Create a mock user repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_thought_repository(self):
        """Create a mock thought repository."""
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_database, mock_user_repository, mock_thought_repository):
        """Create the use case with mocked dependencies."""
        return GetSystemHealthUseCase(
            mock_database, mock_user_repository, mock_thought_repository
        )

    async def test_execute_returns_healthy_status(
        self, use_case, mock_database, mock_user_repository, mock_thought_repository
    ):
        """Test that execute returns healthy status when all services are working."""
        # Arrange
        mock_user_repository.find_all.return_value = []
        mock_thought_repository.find_by_user.return_value = []

        # Act
        result = await use_case.execute()

        # Assert
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert "services" in result
        assert "statistics" in result
        assert result["services"]["database"]["status"] == "healthy"
        assert result["statistics"]["users_accessible"] is True
        assert result["statistics"]["thoughts_accessible"] is True

    async def test_execute_returns_degraded_status_on_db_error(
        self, use_case, mock_database, mock_user_repository, mock_thought_repository
    ):
        """Test that execute returns degraded status when database fails."""
        # Arrange
        mock_database.session.return_value.__aenter__.side_effect = Exception(
            "Database connection failed"
        )
        mock_user_repository.find_all.return_value = []
        mock_thought_repository.find_by_user.return_value = []

        # Act
        result = await use_case.execute()

        # Assert
        assert result["status"] == "degraded"
        assert result["services"]["database"]["status"] == "unhealthy"
        assert "Database connection failed" in result["services"]["database"]["message"]

    async def test_execute_returns_degraded_status_on_repository_error(
        self, use_case, mock_database, mock_user_repository, mock_thought_repository
    ):
        """Test that execute returns degraded status when repositories fail."""
        # Arrange
        mock_user_repository.find_all.side_effect = Exception("Repository error")
        mock_thought_repository.find_by_user.return_value = []

        # Act
        result = await use_case.execute()

        # Assert
        assert result["status"] == "degraded"
        assert "error" in result["statistics"]
        assert "Repository error" in result["statistics"]["error"]

    async def test_execute_calls_repositories_with_correct_parameters(
        self, use_case, mock_database, mock_user_repository, mock_thought_repository
    ):
        """Test that repositories are called with correct parameters."""
        # Arrange
        mock_user_repository.find_all.return_value = []
        mock_thought_repository.find_by_user.return_value = []

        # Act
        await use_case.execute()

        # Assert
        mock_user_repository.find_all.assert_called_once_with(limit=1)
        mock_thought_repository.find_by_user.assert_called_once()
        
        # Verify that find_by_user was called with a UUID
        call_args = mock_thought_repository.find_by_user.call_args
        assert call_args[1]["skip"] == 0
        assert call_args[1]["limit"] == 1
        # The user_id should be a UUID (we can't predict the exact value)