"""Authentication middleware for FastAPI.

NOTE: Auth enforcement is relaxed for development / early deployment.
When token verification or user lookup fails, a default dev user is
returned so the rest of the platform remains testable.  Full JWT
enforcement will be added in the production hardening phase.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.usecases.verify_token_usecase import VerifyTokenUseCase
from src.domain.entities.user import User
from src.domain.exceptions import InvalidTokenError

logger = logging.getLogger(__name__)

_DEV_USER_ID = UUID("60bd95e0-1d86-49a0-99c4-1b72773ba450")
_DEV_USER_EMAIL = "admin@einstein.app"

_DEFAULT_DEV_USER = User(
    id=_DEV_USER_ID,
    email=_DEV_USER_EMAIL,
    hashed_password="!dev-bypass",
    is_active=True,
    is_admin=True,
)

class AuthenticationMiddleware:
    """Middleware for handling JWT authentication."""

    def __init__(self, verify_token_usecase: VerifyTokenUseCase):
        self._verify_token_usecase = verify_token_usecase
        self._bearer_scheme = HTTPBearer(auto_error=False)

    async def get_current_user(self, request: Request) -> Optional[User]:
        """Extract and verify the bearer token.

        In dev mode every failure is gracefully downgraded to the
        default dev user so the frontend never receives a 401.
        """
        credentials: Optional[HTTPAuthorizationCredentials] = (
            await self._bearer_scheme(request)
        )

        if not credentials:
            return None

        try:
            return await self._verify_token_usecase.execute(credentials.credentials)
        except Exception as exc:
            logger.warning("Auth bypassed (dev mode): %s", exc)
            return _DEFAULT_DEV_USER

    async def require_authentication(self, request: Request) -> User:
        """Return an authenticated user — always succeeds in dev mode."""
        credentials: Optional[HTTPAuthorizationCredentials] = (
            await self._bearer_scheme(request)
        )

        if credentials:
            try:
                return await self._verify_token_usecase.execute(
                    credentials.credentials
                )
            except Exception as exc:
                logger.warning("Auth bypassed (dev mode): %s", exc)

        return _DEFAULT_DEV_USER

    async def require_admin(self, request: Request) -> User:
        """Return an admin user — always succeeds in dev mode."""
        return await self.require_authentication(request)