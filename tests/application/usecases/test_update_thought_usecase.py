"""Tests for UpdateThoughtUseCase."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.application.usecases.update_thought_usecase import UpdateThoughtUseCase
from src.domain.entities.enums import EntityType
from src.domain.entities.semantic_entry import SemanticEntry
from src.domain.entities.thought import Thought, ThoughtMetadata, GeoLocation
from src.domain.exceptions import EntityExtractionError, ThoughtNotFoundError
from src.domain.repositories.semantic_entry_repository import SemanticEntryRepository
from src.domain.repositories.thought_repository import ThoughtRepository
from src.domain.services.entity_extraction_service import EntityExtractionService


class TestUpdateThoughtUseCase:
    """Test cases for UpdateThoughtUseCase."""

    @pytest.fixture
    def thought_repository(self):
        """Mock thought repository."""
        return Mock(spec=ThoughtRepository)

    @pytest.fixture
    def semantic_entry_repository(self):
        """Mock semantic entry repository."""
        return Mock(spec=SemanticEntryRepository)

    @pytest.fixture
    def entity_extraction_service(self):
        """Mock entity extraction service."""
        return Mock(spec=EntityExtractionService)

    @pytest.fixture
    def use_case(self, thought_repository, semantic_entry_repository, entity_extraction_service):
        """Create use case instance with mocked dependencies."""
        return UpdateThoughtUseCase(
            thought_repository=thought_repository,
            semantic_entry_repository=semantic_entry_repository,
            entity_extraction_service=entity_extraction_service,
        )

    @pytest.fixture
    def existing_thought(self):
        """Sample existing thought for testing."""
        return Thought(
            id=uuid4(),
            user_id=uuid4(),
            content="Original content",
            timestamp=datetime(2023, 1, 1, 10, 0, 0),
            metadata=ThoughtMetadata(),
            created_at=datetime(2023, 1, 1, 10, 0, 0),
            updated_at=datetime(2023, 1, 1, 10, 0, 0),
        )

    async def test_updates_thought_content_with_entity_reprocessing(
        self, use_case, thought_repository, semantic_entry_repository, 
        entity_extraction_service, existing_thought
    ):
        """Test updating thought content with entity re-processing."""
        # Arrange
        new_content = "Updated content with new entities"
        new_semantic_entries = [
            SemanticEntry(
                id=uuid4(),
                thought_id=existing_thought.id,
                entity_type=EntityType.ACTIVITY,
                entity_value="updated",
                confidence=0.9,
                context="Updated content",
            )
        ]

        thought_repository.find_by_id = AsyncMock(return_value=existing_thought)
        semantic_entry_repository.delete_by_thought = AsyncMock()
        entity_extraction_service.extract_entities = AsyncMock(return_value=new_semantic_entries)
        semantic_entry_repository.save_many = AsyncMock(return_value=new_semantic_entries)
        
        updated_thought = existing_thought.model_copy(
            update={
                "content": new_content,
                "semantic_entries": new_semantic_entries,
                "updated_at": datetime.now(),
            }
        )
        thought_repository.update = AsyncMock(return_value=updated_thought)

        # Act
        result = await use_case.execute(
            thought_id=existing_thought.id,
            user_id=existing_thought.user_id,
            content=new_content,
        )

        # Assert
        assert result.content == new_content
        assert len(result.semantic_entries) == 1
        
        thought_repository.find_by_id.assert_called_once_with(existing_thought.id)
        semantic_entry_repository.delete_by_thought.assert_called_once_with(existing_thought.id)
        entity_extraction_service.extract_entities.assert_called_once_with(
            content=new_content,
            thought_id=existing_thought.id,
            metadata=existing_thought.metadata,
        )
        semantic_entry_repository.save_many.assert_called_once_with(new_semantic_entries)
        thought_repository.update.assert_called_once()

    async def test_updates_thought_metadata_without_entity_reprocessing(
        self, use_case, thought_repository, semantic_entry_repository, 
        entity_extraction_service, existing_thought
    ):
        """Test updating thought metadata without entity re-processing."""
        # Arrange
        new_metadata = ThoughtMetadata(
            location=GeoLocation(latitude=40.7128, longitude=-74.0060),
            mood="happy"
        )

        thought_repository.find_by_id = AsyncMock(return_value=existing_thought)
        updated_thought = existing_thought.model_copy(
            update={"metadata": new_metadata, "updated_at": datetime.now()}
        )
        thought_repository.update = AsyncMock(return_value=updated_thought)

        # Act
        result = await use_case.execute(
            thought_id=existing_thought.id,
            user_id=existing_thought.user_id,
            metadata=new_metadata,
        )

        # Assert
        assert result.metadata == new_metadata
        assert result.content == existing_thought.content  # Content unchanged
        
        thought_repository.find_by_id.assert_called_once_with(existing_thought.id)
        semantic_entry_repository.delete_by_thought.assert_not_called()
        entity_extraction_service.extract_entities.assert_not_called()
        semantic_entry_repository.save_many.assert_not_called()
        thought_repository.update.assert_called_once()

    async def test_updates_both_content_and_metadata(
        self, use_case, thought_repository, semantic_entry_repository, 
        entity_extraction_service, existing_thought
    ):
        """Test updating both content and metadata."""
        # Arrange
        new_content = "New content"
        new_metadata = ThoughtMetadata(mood="excited")
        new_semantic_entries = []

        thought_repository.find_by_id = AsyncMock(return_value=existing_thought)
        semantic_entry_repository.delete_by_thought = AsyncMock()
        entity_extraction_service.extract_entities = AsyncMock(return_value=new_semantic_entries)
        
        updated_thought = existing_thought.model_copy(
            update={
                "content": new_content,
                "metadata": new_metadata,
                "semantic_entries": new_semantic_entries,
                "updated_at": datetime.now(),
            }
        )
        thought_repository.update = AsyncMock(return_value=updated_thought)

        # Act
        result = await use_case.execute(
            thought_id=existing_thought.id,
            user_id=existing_thought.user_id,
            content=new_content,
            metadata=new_metadata,
        )

        # Assert
        assert result.content == new_content
        assert result.metadata == new_metadata
        
        entity_extraction_service.extract_entities.assert_called_once_with(
            content=new_content,
            thought_id=existing_thought.id,
            metadata=new_metadata,
        )

    async def test_raises_error_when_thought_not_found(
        self, use_case, thought_repository
    ):
        """Test error handling when thought is not found."""
        # Arrange
        thought_id = uuid4()
        user_id = uuid4()
        thought_repository.find_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ThoughtNotFoundError) as exc_info:
            await use_case.execute(
                thought_id=thought_id,
                user_id=user_id,
                content="New content",
            )
        
        assert exc_info.value.thought_id == thought_id
        thought_repository.find_by_id.assert_called_once_with(thought_id)

    async def test_raises_error_when_user_not_owner(
        self, use_case, thought_repository, existing_thought
    ):
        """Test error handling when user is not the owner."""
        # Arrange
        different_user_id = uuid4()
        thought_repository.find_by_id = AsyncMock(return_value=existing_thought)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await use_case.execute(
                thought_id=existing_thought.id,
                user_id=different_user_id,
                content="New content",
            )
        
        assert "User does not have permission to update this thought" in str(exc_info.value)
        thought_repository.find_by_id.assert_called_once_with(existing_thought.id)

    async def test_handles_entity_extraction_failure(
        self, use_case, thought_repository, semantic_entry_repository, 
        entity_extraction_service, existing_thought
    ):
        """Test handling of entity extraction failure."""
        # Arrange
        new_content = "New content"
        thought_repository.find_by_id = AsyncMock(return_value=existing_thought)
        semantic_entry_repository.delete_by_thought = AsyncMock()
        entity_extraction_service.extract_entities = AsyncMock(
            side_effect=Exception("LLM service unavailable")
        )

        # Act & Assert
        with pytest.raises(EntityExtractionError) as exc_info:
            await use_case.execute(
                thought_id=existing_thought.id,
                user_id=existing_thought.user_id,
                content=new_content,
            )
        
        assert "Failed to extract entities" in str(exc_info.value)
        assert "LLM service unavailable" in str(exc_info.value)
        
        semantic_entry_repository.delete_by_thought.assert_called_once_with(existing_thought.id)
        entity_extraction_service.extract_entities.assert_called_once()

    async def test_handles_same_content_update_gracefully(
        self, use_case, thought_repository, semantic_entry_repository, 
        entity_extraction_service, existing_thought
    ):
        """Test updating with the same content (should not trigger re-processing)."""
        # Arrange
        same_content = existing_thought.content
        thought_repository.find_by_id = AsyncMock(return_value=existing_thought)
        
        updated_thought = existing_thought.model_copy(update={"updated_at": datetime.now()})
        thought_repository.update = AsyncMock(return_value=updated_thought)

        # Act
        result = await use_case.execute(
            thought_id=existing_thought.id,
            user_id=existing_thought.user_id,
            content=same_content,
        )

        # Assert
        assert result.content == same_content
        
        # Should not trigger entity re-processing since content didn't change
        semantic_entry_repository.delete_by_thought.assert_not_called()
        entity_extraction_service.extract_entities.assert_not_called()
        semantic_entry_repository.save_many.assert_not_called()
        thought_repository.update.assert_called_once()

    async def test_updates_thought_with_no_new_entities(
        self, use_case, thought_repository, semantic_entry_repository, 
        entity_extraction_service, existing_thought
    ):
        """Test updating thought when no new entities are extracted."""
        # Arrange
        new_content = "Simple content with no entities"
        thought_repository.find_by_id = AsyncMock(return_value=existing_thought)
        semantic_entry_repository.delete_by_thought = AsyncMock()
        entity_extraction_service.extract_entities = AsyncMock(return_value=[])
        
        updated_thought = existing_thought.model_copy(
            update={
                "content": new_content,
                "semantic_entries": [],
                "updated_at": datetime.now(),
            }
        )
        thought_repository.update = AsyncMock(return_value=updated_thought)

        # Act
        result = await use_case.execute(
            thought_id=existing_thought.id,
            user_id=existing_thought.user_id,
            content=new_content,
        )

        # Assert
        assert result.content == new_content
        assert len(result.semantic_entries) == 0
        
        semantic_entry_repository.delete_by_thought.assert_called_once_with(existing_thought.id)
        entity_extraction_service.extract_entities.assert_called_once()
        semantic_entry_repository.save_many.assert_not_called()
        thought_repository.update.assert_called_once()