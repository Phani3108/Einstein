"""Update thought use case for the Personal Semantic Engine."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from src.domain.entities.thought import Thought, ThoughtMetadata
from src.domain.exceptions import EntityExtractionError, ThoughtNotFoundError
from src.domain.repositories.semantic_entry_repository import SemanticEntryRepository
from src.domain.repositories.thought_repository import ThoughtRepository
from src.domain.services.entity_extraction_service import EntityExtractionService


class UpdateThoughtUseCase:
    """Use case for updating a thought with re-processing of entities."""

    def __init__(
        self,
        thought_repository: ThoughtRepository,
        semantic_entry_repository: SemanticEntryRepository,
        entity_extraction_service: EntityExtractionService,
    ):
        """Initialize the use case with required dependencies.

        Args:
            thought_repository: Repository for thought persistence
            semantic_entry_repository: Repository for semantic entry persistence
            entity_extraction_service: Service for extracting entities from content
        """
        self._thought_repository = thought_repository
        self._semantic_entry_repository = semantic_entry_repository
        self._entity_extraction_service = entity_extraction_service

    async def execute(
        self,
        thought_id: UUID,
        user_id: UUID,
        content: Optional[str] = None,
        metadata: Optional[ThoughtMetadata] = None,
    ) -> Thought:
        """Update a thought with optional re-processing of entities.

        Args:
            thought_id: The ID of the thought to update
            user_id: The ID of the user who owns the thought (for authorization)
            content: Optional new content for the thought
            metadata: Optional new metadata for the thought

        Returns:
            The updated thought with re-processed semantic entries

        Raises:
            ThoughtNotFoundError: If the thought does not exist
            ValueError: If the user does not own the thought
            EntityExtractionError: If entity extraction fails
        """
        # Find the existing thought
        existing_thought = await self._thought_repository.find_by_id(thought_id)
        if not existing_thought:
            raise ThoughtNotFoundError(thought_id)

        # Verify ownership
        if existing_thought.user_id != user_id:
            raise ValueError("User does not have permission to update this thought")

        # Determine what needs to be updated
        updated_content = content if content is not None else existing_thought.content
        updated_metadata = metadata if metadata is not None else existing_thought.metadata
        
        # Check if content changed (requires entity re-processing)
        content_changed = content is not None and content != existing_thought.content

        # Create updated thought
        updated_thought = existing_thought.model_copy(
            update={
                "content": updated_content,
                "metadata": updated_metadata,
                "updated_at": datetime.now(),
            }
        )

        # If content changed, we need to re-process entities
        if content_changed:
            # Delete existing semantic entries
            await self._semantic_entry_repository.delete_by_thought(thought_id)

            # Extract new entities from the updated content
            try:
                semantic_entries = await self._entity_extraction_service.extract_entities(
                    content=updated_content,
                    thought_id=thought_id,
                    metadata=updated_metadata,
                )
            except Exception as e:
                raise EntityExtractionError(f"Failed to extract entities: {str(e)}")

            # Save the new semantic entries
            if semantic_entries:
                saved_entries = await self._semantic_entry_repository.save_many(
                    semantic_entries
                )
                updated_thought = updated_thought.model_copy(
                    update={"semantic_entries": saved_entries}
                )
            else:
                updated_thought = updated_thought.model_copy(
                    update={"semantic_entries": []}
                )

        # Save and return the updated thought
        return await self._thought_repository.update(updated_thought)