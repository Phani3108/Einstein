"""Get thought by ID use case for the Personal Semantic Engine."""

from typing import Optional
from uuid import UUID

from src.domain.entities.thought import Thought
from src.domain.exceptions import ThoughtNotFoundError
from src.domain.repositories.thought_repository import ThoughtRepository


class GetThoughtByIdUseCase:
    """Use case for retrieving a specific thought by ID."""

    def __init__(self, thought_repository: ThoughtRepository):
        """Initialize the use case with required dependencies.

        Args:
            thought_repository: Repository for thought data access
        """
        self._thought_repository = thought_repository

    async def execute(self, thought_id: UUID, user_id: UUID) -> Thought:
        """Get a specific thought by ID.

        Args:
            thought_id: The ID of the thought to retrieve
            user_id: The ID of the user requesting the thought (for authorization)

        Returns:
            The requested thought

        Raises:
            ThoughtNotFoundError: If the thought does not exist
            ValueError: If the user does not own the thought
        """
        thought = await self._thought_repository.find_by_id(thought_id)
        if not thought:
            raise ThoughtNotFoundError(thought_id)

        # Verify ownership
        if thought.user_id != user_id:
            raise ValueError("User does not have permission to access this thought")

        return thought