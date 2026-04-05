"""Thought repository interface for the Personal Semantic Engine."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from src.domain.entities.thought import Thought


class ThoughtRepository(ABC):
    """Interface for thought data access."""

    @abstractmethod
    async def save(self, thought: Thought) -> Thought:
        """Save a thought to the repository.

        Args:
            thought: The thought to save

        Returns:
            The saved thought with any generated fields populated
        """
        pass

    @abstractmethod
    async def find_by_id(self, thought_id: UUID) -> Optional[Thought]:
        """Find a thought by its ID.

        Args:
            thought_id: The ID of the thought to find

        Returns:
            The thought if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Thought]:
        """Find thoughts by user ID.

        Args:
            user_id: The ID of the user whose thoughts to find
            skip: Number of thoughts to skip for pagination
            limit: Maximum number of thoughts to return

        Returns:
            A list of thoughts belonging to the user
        """
        pass

    @abstractmethod
    async def update(self, thought: Thought) -> Thought:
        """Update a thought in the repository.

        Args:
            thought: The thought to update

        Returns:
            The updated thought

        Raises:
            ThoughtNotFoundError: If the thought does not exist
        """
        pass

    @abstractmethod
    async def delete(self, thought_id: UUID) -> None:
        """Delete a thought from the repository.

        Args:
            thought_id: The ID of the thought to delete

        Raises:
            ThoughtNotFoundError: If the thought does not exist
        """
        pass
