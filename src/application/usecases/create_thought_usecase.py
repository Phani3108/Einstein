"""Create thought use case for the Personal Semantic Engine."""

from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from src.domain.entities.semantic_entry import SemanticEntry
from src.domain.entities.thought import Thought, ThoughtMetadata
from src.domain.exceptions import EntityExtractionError
from src.domain.repositories.semantic_entry_repository import SemanticEntryRepository
from src.domain.repositories.thought_repository import ThoughtRepository
from src.domain.services.entity_extraction_service import EntityExtractionService


class CreateThoughtUseCase:
    """Use case for creating a new thought with entity extraction."""

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
        user_id: UUID,
        content: str,
        metadata: ThoughtMetadata = None,
        timestamp: datetime = None,
    ) -> Thought:
        """Create a new thought with entity extraction and storage.

        Args:
            user_id: The ID of the user creating the thought
            content: The thought content
            metadata: Optional metadata for the thought
            timestamp: Optional timestamp, defaults to current time

        Returns:
            The created thought with extracted semantic entries

        Raises:
            EntityExtractionError: If entity extraction fails
        """
        # Create the thought entity
        thought_id = uuid4()
        thought = Thought(
            id=thought_id,
            user_id=user_id,
            content=content,
            timestamp=timestamp or datetime.now(),
            metadata=metadata or ThoughtMetadata(),
        )

        # Save the thought first
        saved_thought = await self._thought_repository.save(thought)

        # Extract entities from the thought content
        try:
            semantic_entries = await self._entity_extraction_service.extract_entities(
                content=content,
                thought_id=thought_id,
                metadata=metadata,
            )
        except Exception as e:
            # If entity extraction fails, we still keep the thought but log the error
            # This ensures the user's data is not lost due to processing failures
            raise EntityExtractionError(f"Failed to extract entities: {str(e)}")

        # Save the extracted semantic entries
        if semantic_entries:
            saved_entries = await self._semantic_entry_repository.save_many(
                semantic_entries
            )
            
            # Update the thought with the semantic entries
            updated_thought = saved_thought.model_copy(
                update={"semantic_entries": saved_entries, "updated_at": datetime.now()}
            )
            
            # Save the updated thought with semantic entries
            final_thought = await self._thought_repository.update(updated_thought)
            return final_thought

        return saved_thought