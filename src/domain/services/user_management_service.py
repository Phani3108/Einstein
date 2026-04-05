"""User management service interface for the Personal Semantic Engine."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.domain.entities.user import User


class UserRegistrationData:
    """Data for user registration."""
    
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password


class UserManagementService(ABC):
    """Interface for user management operations."""

    @abstractmethod
    async def register_user(self, registration_data: UserRegistrationData) -> User:
        """Register a new user.

        Args:
            registration_data: User registration information

        Returns:
            The created user

        Raises:
            UserAlreadyExistsError: If user with email already exists
            UserRegistrationError: If registration fails
        """
        pass

    @abstractmethod
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password.

        Args:
            email: User's email address
            password: User's plain text password

        Returns:
            The authenticated user if credentials are valid, None otherwise

        Raises:
            AuthenticationError: If authentication process fails
        """
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get a user by their ID.

        Args:
            user_id: The user's ID

        Returns:
            The user if found, None otherwise

        Raises:
            UserManagementError: If retrieval fails
        """
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by their email address.

        Args:
            email: The user's email address

        Returns:
            The user if found, None otherwise

        Raises:
            UserManagementError: If retrieval fails
        """
        pass

    @abstractmethod
    async def update_last_login(self, user_id: UUID) -> None:
        """Update the user's last login timestamp.

        Args:
            user_id: The user's ID

        Raises:
            UserNotFoundError: If user doesn't exist
            UserManagementError: If update fails
        """
        pass

    @abstractmethod
    async def deactivate_user(self, user_id: UUID) -> None:
        """Deactivate a user account.

        Args:
            user_id: The user's ID

        Raises:
            UserNotFoundError: If user doesn't exist
            UserManagementError: If deactivation fails
        """
        pass

    @abstractmethod
    async def activate_user(self, user_id: UUID) -> None:
        """Activate a user account.

        Args:
            user_id: The user's ID

        Raises:
            UserNotFoundError: If user doesn't exist
            UserManagementError: If activation fails
        """
        pass