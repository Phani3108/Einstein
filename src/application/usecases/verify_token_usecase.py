"""Verify token use case for the Personal Semantic Engine."""

from typing import Optional

from src.domain.entities.user import User
from src.domain.exceptions import InvalidTokenError
from src.domain.services.authentication_service import AuthenticationService, TokenData
from src.domain.services.user_management_service import UserManagementService


class VerifyTokenUseCase:
    """Use case for verifying authentication tokens."""

    def __init__(
        self,
        authentication_service: AuthenticationService,
        user_management_service: UserManagementService,
    ):
        """Initialize the use case with required dependencies.

        Args:
            authentication_service: Service for authentication operations
            user_management_service: Service for user management operations
        """
        self._authentication_service = authentication_service
        self._user_management_service = user_management_service

    async def execute(self, token: str) -> User:
        """Verify a token and return the associated user.

        Args:
            token: The JWT token to verify

        Returns:
            The user associated with the token

        Raises:
            InvalidTokenError: If token is invalid, expired, or user doesn't exist
        """
        # Verify the token
        token_data: TokenData = await self._authentication_service.verify_token(token)

        # Get the user from the database to ensure they still exist and are active
        user: Optional[User] = await self._user_management_service.get_user_by_id(
            token_data.user_id
        )

        if not user:
            raise InvalidTokenError("User associated with token no longer exists")

        if not user.is_active:
            raise InvalidTokenError("User account is deactivated")

        return user