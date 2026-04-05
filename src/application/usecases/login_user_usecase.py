"""Login user use case for the Personal Semantic Engine."""

from typing import Optional

from src.domain.entities.user import User
from src.domain.exceptions import AuthenticationError
from src.domain.services.authentication_service import AuthenticationService
from src.domain.services.user_management_service import UserManagementService


class LoginResult:
    """Result of a login operation."""

    def __init__(self, user: User, access_token: str):
        self.user = user
        self.access_token = access_token


class LoginUserUseCase:
    """Use case for user login and authentication."""

    def __init__(
        self,
        user_management_service: UserManagementService,
        authentication_service: AuthenticationService,
    ):
        """Initialize the use case with required dependencies.

        Args:
            user_management_service: Service for user management operations
            authentication_service: Service for authentication operations
        """
        self._user_management_service = user_management_service
        self._authentication_service = authentication_service

    async def execute(self, email: str, password: str) -> LoginResult:
        """Authenticate a user and generate an access token.

        Args:
            email: User's email address
            password: User's plain text password

        Returns:
            LoginResult containing user and access token

        Raises:
            AuthenticationError: If authentication fails
        """
        # Validate input
        if not email or not email.strip():
            raise AuthenticationError("Email is required")

        if not password:
            raise AuthenticationError("Password is required")

        # Authenticate user
        user = await self._user_management_service.authenticate_user(
            email.strip().lower(), password
        )

        if not user:
            raise AuthenticationError("Invalid email or password")

        # Generate access token
        access_token = await self._authentication_service.create_access_token(user)

        # Update last login timestamp
        await self._user_management_service.update_last_login(user.id)

        return LoginResult(user=user, access_token=access_token)