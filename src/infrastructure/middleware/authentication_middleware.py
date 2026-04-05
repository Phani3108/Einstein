"""Authentication middleware for FastAPI."""

from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.usecases.verify_token_usecase import VerifyTokenUseCase
from src.domain.entities.user import User
from src.domain.exceptions import InvalidTokenError


class AuthenticationMiddleware:
    """Middleware for handling JWT authentication."""

    def __init__(self, verify_token_usecase: VerifyTokenUseCase):
        """Initialize the authentication middleware.

        Args:
            verify_token_usecase: Use case for token verification
        """
        self._verify_token_usecase = verify_token_usecase
        self._bearer_scheme = HTTPBearer(auto_error=False)

    async def get_current_user(self, request: Request) -> Optional[User]:
        """Get the current authenticated user from the request.

        Args:
            request: The FastAPI request object

        Returns:
            The authenticated user if token is valid, None otherwise

        Raises:
            HTTPException: If authentication fails
        """
        credentials: Optional[HTTPAuthorizationCredentials] = await self._bearer_scheme(
            request
        )

        if not credentials:
            return None

        try:
            user = await self._verify_token_usecase.execute(credentials.credentials)
            return user

        except InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def require_authentication(self, request: Request) -> User:
        """Require authentication and return the current user.

        Args:
            request: The FastAPI request object

        Returns:
            The authenticated user

        Raises:
            HTTPException: If authentication fails or is missing
        """
        user = await self.get_current_user(request)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    async def require_admin(self, request: Request) -> User:
        """Require admin authentication and return the current user.

        Args:
            request: The FastAPI request object

        Returns:
            The authenticated admin user

        Raises:
            HTTPException: If authentication fails or user is not admin
        """
        user = await self.require_authentication(request)

        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

        return user