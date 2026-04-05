"""Register user use case for the Personal Semantic Engine."""

from src.domain.entities.user import User
from src.domain.exceptions import UserAlreadyExistsError, UserRegistrationError
from src.domain.services.user_management_service import (
    UserManagementService,
    UserRegistrationData,
)


class RegisterUserUseCase:
    """Use case for registering a new user."""

    def __init__(self, user_management_service: UserManagementService):
        """Initialize the use case with required dependencies.

        Args:
            user_management_service: Service for user management operations
        """
        self._user_management_service = user_management_service

    async def execute(self, email: str, password: str) -> User:
        """Register a new user.

        Args:
            email: User's email address
            password: User's plain text password

        Returns:
            The created user

        Raises:
            UserAlreadyExistsError: If user with email already exists
            UserRegistrationError: If registration fails
        """
        # Validate input
        if not email or not email.strip():
            raise UserRegistrationError("Email is required")

        if not password or len(password) < 8:
            raise UserRegistrationError("Password must be at least 8 characters long")

        # Create registration data
        registration_data = UserRegistrationData(
            email=email.strip().lower(),
            password=password,
        )

        # Register the user
        user = await self._user_management_service.register_user(registration_data)
        return user