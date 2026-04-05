"""Delete thought use case for the Personal Semantic Engine."""

from uuid import UUID

from src.domain.exceptions import ThoughtNotFoundError
from src.domain.repositories.semantic_entry_repository import SemanticEntryRepository
from src.domain.repositories.thought_repository import ThoughtRepository


class DeleteThoughtUseCase:
    """Use case for deleting a thought with cleanup of related entities."""

    def __init__(
        self,
        thought_repository: ThoughtRepository,
        semantic_entry_repository: SemanticEntryRepository,
    ):
        """Initialize the use case with required dependencies.

        Args:
            thought_repository: Repository for thought persistence
            semantic_entry_repository: Repository for semantic entry persistence
        """
        self._thought_repository = thought_repository
        self._semantic_entry_repository = semantic_entry_repository

    async def execute(self, thought_id: UUID, user_id: UUID) -> None:
        """Delete a thought and all its related semantic entries.

        Args:
            thought_id: The ID of the thought to delete
            user_id: The ID of the user who owns the thought (for authorization)

        Raises:
            ThoughtNotFoundError: If the thought does not exist
            ValueError: If the user does not own the thought
        """
        # Find the existing thought to verify ownership
        existing_thought = await self._thought_repository.find_by_id(thought_id)
        if not existing_thought:
            raise ThoughtNotFoundError(thought_id)

        # Verify ownership
        if existing_thought.user_id != user_id:
            raise ValueError("User does not have permission to delete this thought")

        # Delete related semantic entries first (to maintain referential integrity)
        await self._semantic_entry_repository.delete_by_thought(thought_id)

        # Delete the thought
        await self._thought_repository.delete(thought_id)