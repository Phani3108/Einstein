"""User repository interface for the Personal Semantic Engine."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from src.domain.entities.user import User


class UserRepository(ABC):
    """Interface for user data access."""

    @abstractmethod
    async def save(self, user: User) -> User:
        """Save a user to the repository.

        Args:
            user: The user to save

        Returns:
            The saved user with any generated fields populated
        """
        pass

    @abstractmethod
    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        """Find a user by their ID.

        Args:
            user_id: The ID of the user to find

        Returns:
            The user if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        """Find a user by their email.

        Args:
            email: The email of the user to find

        Returns:
            The user if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Find all users.

        Args:
            skip: Number of users to skip for pagination
            limit: Maximum number of users to return

        Returns:
            A list of users
        """
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update a user in the repository.

        Args:
            user: The user to update

        Returns:
            The updated user

        Raises:
            UserNotFoundError: If the user does not exist
        """
        pass

    @abstractmethod
    async def delete(self, user_id: UUID) -> None:
        """Delete a user from the repository.

        Args:
            user_id: The ID of the user to delete

        Raises:
            UserNotFoundError: If the user does not exist
        """
        pass
