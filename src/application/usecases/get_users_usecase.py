"""Get users use case for admin functionality."""

from typing import List

from src.domain.entities.user import User
from src.domain.repositories.user_repository import UserRepository


class GetUsersUseCase:
    """Use case for retrieving all users (admin only)."""

    def __init__(self, user_repository: UserRepository):
        """Initialize the use case.

        Args:
            user_repository: Repository for user data access
        """
        self._user_repository = user_repository

    async def execute(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Execute the get users use case.

        Args:
            skip: Number of users to skip for pagination
            limit: Maximum number of users to return

        Returns:
            List of users

        Raises:
            RepositoryError: If database operation fails
        """
        return await self._user_repository.find_all(skip=skip, limit=limit)