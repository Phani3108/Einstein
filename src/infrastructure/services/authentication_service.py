"""JWT-based authentication service implementation."""

import os
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from src.domain.entities.user import User
from src.domain.exceptions import AuthenticationError, InvalidTokenError, TokenError
from src.domain.services.authentication_service import AuthenticationService, TokenData


class JWTAuthenticationService(AuthenticationService):
    """JWT-based authentication service implementation."""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 1440,  # 24 hours
    ):
        """Initialize the JWT authentication service.

        Args:
            secret_key: Secret key for JWT signing
            algorithm: JWT algorithm to use
            access_token_expire_minutes: Token expiration time in minutes
        """
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_token_expire_minutes = access_token_expire_minutes

    async def create_access_token(
        self, user: User, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token for a user.

        Args:
            user: The user to create a token for
            expires_delta: Optional custom expiration time

        Returns:
            A JWT access token string

        Raises:
            AuthenticationError: If token creation fails
        """
        try:
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(
                    minutes=self._access_token_expire_minutes
                )

            to_encode = {
                "sub": str(user.id),
                "email": user.email,
                "is_admin": user.is_admin,
                "exp": expire,
                "iat": datetime.utcnow(),
            }

            encoded_jwt = jwt.encode(to_encode, self._secret_key, algorithm=self._algorithm)
            return encoded_jwt

        except Exception as e:
            raise AuthenticationError(f"Failed to create access token: {str(e)}")

    async def verify_token(self, token: str) -> TokenData:
        """Verify and decode a JWT token.

        Args:
            token: The JWT token to verify

        Returns:
            TokenData containing user information

        Raises:
            InvalidTokenError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
            
            user_id_str: str = payload.get("sub")
            if user_id_str is None:
                raise InvalidTokenError("Token missing user ID")

            user_id = UUID(user_id_str)
            email: str = payload.get("email")
            if email is None:
                raise InvalidTokenError("Token missing email")

            is_admin: bool = payload.get("is_admin", False)
            exp_timestamp = payload.get("exp")
            expires_at = datetime.fromtimestamp(exp_timestamp) if exp_timestamp else None

            return TokenData(
                user_id=user_id,
                email=email,
                is_admin=is_admin,
                expires_at=expires_at,
            )

        except JWTError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}")
        except ValueError as e:
            raise InvalidTokenError(f"Invalid user ID in token: {str(e)}")
        except Exception as e:
            raise InvalidTokenError(f"Token verification failed: {str(e)}")

    async def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: The plain text password to hash

        Returns:
            The hashed password string

        Raises:
            AuthenticationError: If hashing fails
        """
        try:
            # Generate salt and hash password
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
            return hashed.decode("utf-8")

        except Exception as e:
            raise AuthenticationError(f"Failed to hash password: {str(e)}")

    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash using bcrypt.

        Args:
            plain_password: The plain text password
            hashed_password: The hashed password to verify against

        Returns:
            True if password matches, False otherwise

        Raises:
            AuthenticationError: If verification fails
        """
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"), hashed_password.encode("utf-8")
            )

        except Exception as e:
            raise AuthenticationError(f"Failed to verify password: {str(e)}")

    async def refresh_token(self, token: str) -> str:
        """Refresh an access token.

        Args:
            token: The current access token

        Returns:
            A new access token

        Raises:
            InvalidTokenError: If token refresh fails
        """
        try:
            # Verify the current token
            token_data = await self.verify_token(token)

            # Create a new token with the same user data
            # Note: In a real implementation, you might want to check if the user
            # still exists and is active before issuing a new token
            user = User(
                id=token_data.user_id,
                email=token_data.email,
                hashed_password="",  # Not needed for token refresh
                is_admin=token_data.is_admin,
            )

            return await self.create_access_token(user)

        except InvalidTokenError:
            raise
        except Exception as e:
            raise TokenError(f"Failed to refresh token: {str(e)}")

    @classmethod
    def from_environment(cls) -> "JWTAuthenticationService":
        """Create authentication service from environment variables.

        Returns:
            Configured JWTAuthenticationService instance

        Raises:
            AuthenticationError: If required environment variables are missing
        """
        secret_key = os.getenv("JWT_SECRET_KEY")
        if not secret_key:
            raise AuthenticationError("JWT_SECRET_KEY environment variable is required")

        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

        return cls(
            secret_key=secret_key,
            algorithm=algorithm,
            access_token_expire_minutes=expire_minutes,
        )