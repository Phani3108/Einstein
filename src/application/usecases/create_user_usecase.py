"""Create user use case for admin functionality."""

from datetime import datetime
from uuid import uuid4

from src.domain.entities.user import User
from src.domain.exceptions import UserAlreadyExistsError
from src.domain.repositories.user_repository import UserRepository
from src.domain.services.authentication_service import AuthenticationService


class CreateUserUseCase:
    """Use case for creating a new user (admin only)."""

    def __init__(
        self,
        user_repository: UserRepository,
        authentication_service: AuthenticationService,
    ):
        """Initialize the use case.

        Args:
            user_repository: Repository for user data access
            authentication_service: Service for password hashing
        """
        self._user_repository = user_repository
        self._authentication_service = authentication_service

    async def execute(
        self,
        email: str,
        password: str,
        is_admin: bool = False,
        is_active: bool = True,
    ) -> User:
        """Execute the create user use case.

        Args:
            email: User's email address
            password: User's plain text password
            is_admin: Whether the user should have admin privileges
            is_active: Whether the user account should be active

        Returns:
            The created user

        Raises:
            UserAlreadyExistsError: If a user with the email already exists
            AuthenticationError: If password hashing fails
            RepositoryError: If database operation fails
        """
        # Check if user already exists
        existing_user = await self._user_repository.find_by_email(email)
        if existing_user:
            raise UserAlreadyExistsError(email)

        # Hash the password
        hashed_password = await self._authentication_service.hash_password(password)

        # Create the user
        user = User(
            id=uuid4(),
            email=email,
            hashed_password=hashed_password,
            is_admin=is_admin,
            is_active=is_active,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Save and return the user
        return await self._user_repository.save(user)