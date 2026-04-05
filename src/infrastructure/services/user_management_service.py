"""User management service implementation."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

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
from src.domain.services.user_management_service import (
    UserManagementService,
    UserRegistrationData,
)


class DefaultUserManagementService(UserManagementService):
    """Default implementation of user management service."""

    def __init__(
        self,
        user_repository: UserRepository,
        authentication_service: AuthenticationService,
    ):
        """Initialize the user management service.

        Args:
            user_repository: Repository for user data access
            authentication_service: Service for password hashing and authentication
        """
        self._user_repository = user_repository
        self._authentication_service = authentication_service

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
        try:
            # Check if user already exists
            existing_user = await self._user_repository.find_by_email(registration_data.email)
            if existing_user:
                raise UserAlreadyExistsError(registration_data.email)

            # Hash the password
            hashed_password = await self._authentication_service.hash_password(
                registration_data.password
            )

            # Create the user
            user = User(
                id=uuid4(),
                email=registration_data.email,
                hashed_password=hashed_password,
                is_active=True,
                is_admin=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            # Save the user
            saved_user = await self._user_repository.save(user)
            return saved_user

        except UserAlreadyExistsError:
            raise
        except Exception as e:
            raise UserRegistrationError(f"Failed to register user: {str(e)}")

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
        try:
            # Find user by email
            user = await self._user_repository.find_by_email(email)
            if not user:
                return None

            # Check if user is active
            if not user.is_active:
                return None

            # Verify password
            password_valid = await self._authentication_service.verify_password(
                password, user.hashed_password
            )
            if not password_valid:
                return None

            return user

        except Exception as e:
            raise AuthenticationError(f"Authentication failed: {str(e)}")

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get a user by their ID.

        Args:
            user_id: The user's ID

        Returns:
            The user if found, None otherwise

        Raises:
            UserManagementError: If retrieval fails
        """
        try:
            return await self._user_repository.find_by_id(user_id)

        except Exception as e:
            raise UserManagementError(f"Failed to get user by ID: {str(e)}")

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by their email address.

        Args:
            email: The user's email address

        Returns:
            The user if found, None otherwise

        Raises:
            UserManagementError: If retrieval fails
        """
        try:
            return await self._user_repository.find_by_email(email)

        except Exception as e:
            raise UserManagementError(f"Failed to get user by email: {str(e)}")

    async def update_last_login(self, user_id: UUID) -> None:
        """Update the user's last login timestamp.

        Args:
            user_id: The user's ID

        Raises:
            UserNotFoundError: If user doesn't exist
            UserManagementError: If update fails
        """
        try:
            user = await self._user_repository.find_by_id(user_id)
            if not user:
                raise UserNotFoundError(user_id=user_id)

            # Update last login timestamp
            updated_user = user.model_copy(
                update={
                    "last_login": datetime.now(),
                    "updated_at": datetime.now(),
                }
            )

            await self._user_repository.update(updated_user)

        except UserNotFoundError:
            raise
        except Exception as e:
            raise UserManagementError(f"Failed to update last login: {str(e)}")

    async def deactivate_user(self, user_id: UUID) -> None:
        """Deactivate a user account.

        Args:
            user_id: The user's ID

        Raises:
            UserNotFoundError: If user doesn't exist
            UserManagementError: If deactivation fails
        """
        try:
            user = await self._user_repository.find_by_id(user_id)
            if not user:
                raise UserNotFoundError(user_id=user_id)

            # Deactivate user
            updated_user = user.model_copy(
                update={
                    "is_active": False,
                    "updated_at": datetime.now(),
                }
            )

            await self._user_repository.update(updated_user)

        except UserNotFoundError:
            raise
        except Exception as e:
            raise UserManagementError(f"Failed to deactivate user: {str(e)}")

    async def activate_user(self, user_id: UUID) -> None:
        """Activate a user account.

        Args:
            user_id: The user's ID

        Raises:
            UserNotFoundError: If user doesn't exist
            UserManagementError: If activation fails
        """
        try:
            user = await self._user_repository.find_by_id(user_id)
            if not user:
                raise UserNotFoundError(user_id=user_id)

            # Activate user
            updated_user = user.model_copy(
                update={
                    "is_active": True,
                    "updated_at": datetime.now(),
                }
            )

            await self._user_repository.update(updated_user)

        except UserNotFoundError:
            raise
        except Exception as e:
            raise UserManagementError(f"Failed to activate user: {str(e)}")