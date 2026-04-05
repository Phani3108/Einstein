"""Authentication service interface for the Personal Semantic Engine."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from src.domain.entities.user import User


class TokenData:
    """Token data for JWT authentication."""
    
    def __init__(self, user_id: UUID, email: str, is_admin: bool = False, expires_at: Optional[datetime] = None):
        self.user_id = user_id
        self.email = email
        self.is_admin = is_admin
        self.expires_at = expires_at or (datetime.utcnow() + timedelta(hours=24))


class AuthenticationService(ABC):
    """Interface for authentication operations."""

    @abstractmethod
    async def create_access_token(self, user: User, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token for a user.

        Args:
            user: The user to create a token for
            expires_delta: Optional custom expiration time

        Returns:
            A JWT access token string

        Raises:
            AuthenticationError: If token creation fails
        """
        pass

    @abstractmethod
    async def verify_token(self, token: str) -> TokenData:
        """Verify and decode a JWT token.

        Args:
            token: The JWT token to verify

        Returns:
            TokenData containing user information

        Raises:
            AuthenticationError: If token is invalid or expired
        """
        pass

    @abstractmethod
    async def hash_password(self, password: str) -> str:
        """Hash a password using a secure hashing algorithm.

        Args:
            password: The plain text password to hash

        Returns:
            The hashed password string

        Raises:
            AuthenticationError: If hashing fails
        """
        pass

    @abstractmethod
    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash.

        Args:
            plain_password: The plain text password
            hashed_password: The hashed password to verify against

        Returns:
            True if password matches, False otherwise

        Raises:
            AuthenticationError: If verification fails
        """
        pass

    @abstractmethod
    async def refresh_token(self, token: str) -> str:
        """Refresh an access token.

        Args:
            token: The current access token

        Returns:
            A new access token

        Raises:
            AuthenticationError: If token refresh fails
        """
        pass