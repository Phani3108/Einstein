"""Get thoughts use case for the Personal Semantic Engine."""

from typing import List
from uuid import UUID

from src.domain.entities.thought import Thought
from src.domain.repositories.thought_repository import ThoughtRepository


class GetThoughtsUseCase:
    """Use case for retrieving thoughts with pagination and user filtering."""

    def __init__(self, thought_repository: ThoughtRepository):
        """Initialize the use case with required dependencies.

        Args:
            thought_repository: Repository for thought data access
        """
        self._thought_repository = thought_repository

    async def execute(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Thought]:
        """Get thoughts for a specific user with pagination.

        Args:
            user_id: The ID of the user whose thoughts to retrieve
            skip: Number of thoughts to skip for pagination (default: 0)
            limit: Maximum number of thoughts to return (default: 100)

        Returns:
            A list of thoughts belonging to the user

        Raises:
            ValueError: If skip is negative or limit is not positive
        """
        if skip < 0:
            raise ValueError("Skip parameter must be non-negative")
        
        if limit <= 0:
            raise ValueError("Limit parameter must be positive")
        
        if limit > 1000:
            raise ValueError("Limit parameter cannot exceed 1000")

        return await self._thought_repository.find_by_user(
            user_id=user_id, skip=skip, limit=limit
        )