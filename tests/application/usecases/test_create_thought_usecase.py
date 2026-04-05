"""Tests for CreateThoughtUseCase."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.application.usecases.create_thought_usecase import CreateThoughtUseCase
from src.domain.entities.enums import EntityType
from src.domain.entities.semantic_entry import SemanticEntry
from src.domain.entities.thought import Thought, ThoughtMetadata, GeoLocation
from src.domain.exceptions import EntityExtractionError
from src.domain.repositories.semantic_entry_repository import SemanticEntryRepository
from src.domain.repositories.thought_repository import ThoughtRepository
from src.domain.services.entity_extraction_service import EntityExtractionService


class TestCreateThoughtUseCase:
    """Test cases for CreateThoughtUseCase."""

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
        return CreateThoughtUseCase(
            thought_repository=thought_repository,
            semantic_entry_repository=semantic_entry_repository,
            entity_extraction_service=entity_extraction_service,
        )

    @pytest.fixture
    def sample_thought(self):
        """Sample thought for testing."""
        return Thought(
            id=uuid4(),
            user_id=uuid4(),
            content="I went to the park today and felt happy",
            timestamp=datetime.now(),
            metadata=ThoughtMetadata(),
        )

    @pytest.fixture
    def sample_semantic_entries(self, sample_thought):
        """Sample semantic entries for testing."""
        return [
            SemanticEntry(
                id=uuid4(),
                thought_id=sample_thought.id,
                entity_type=EntityType.LOCATION,
                entity_value="park",
                confidence=0.9,
                context="went to the park today",
            ),
            SemanticEntry(
                id=uuid4(),
                thought_id=sample_thought.id,
                entity_type=EntityType.EMOTION,
                entity_value="happy",
                confidence=0.8,
                context="felt happy",
            ),
        ]

    async def test_creates_thought_with_valid_input_successfully(
        self, use_case, thought_repository, semantic_entry_repository, entity_extraction_service
    ):
        """Test successful thought creation with valid input."""
        # Arrange
        user_id = uuid4()
        content = "I went to the park today and felt happy"
        metadata = ThoughtMetadata(location=GeoLocation(latitude=40.7128, longitude=-74.0060))
        
        saved_thought = Thought(
            id=uuid4(),
            user_id=user_id,
            content=content,
            metadata=metadata,
        )
        
        semantic_entries = [
            SemanticEntry(
                id=uuid4(),
                thought_id=saved_thought.id,
                entity_type=EntityType.LOCATION,
                entity_value="park",
                confidence=0.9,
                context="went to the park today",
            )
        ]

        thought_repository.save = AsyncMock(return_value=saved_thought)
        entity_extraction_service.extract_entities = AsyncMock(return_value=semantic_entries)
        semantic_entry_repository.save_many = AsyncMock(return_value=semantic_entries)
        thought_repository.update = AsyncMock(return_value=saved_thought.model_copy(update={"semantic_entries": semantic_entries}))

        # Act
        result = await use_case.execute(
            user_id=user_id,
            content=content,
            metadata=metadata,
        )

        # Assert
        assert result.user_id == user_id
        assert result.content == content
        assert result.metadata == metadata
        assert len(result.semantic_entries) == 1
        
        thought_repository.save.assert_called_once()
        # Verify extract_entities was called with correct parameters
        extract_call = entity_extraction_service.extract_entities.call_args
        assert extract_call[1]['content'] == content
        assert extract_call[1]['metadata'] == metadata
        assert 'thought_id' in extract_call[1]
        semantic_entry_repository.save_many.assert_called_once_with(semantic_entries)
        thought_repository.update.assert_called_once()

    async def test_creates_thought_without_metadata_successfully(
        self, use_case, thought_repository, semantic_entry_repository, entity_extraction_service
    ):
        """Test successful thought creation without metadata."""
        # Arrange
        user_id = uuid4()
        content = "Simple thought"
        
        saved_thought = Thought(
            id=uuid4(),
            user_id=user_id,
            content=content,
        )

        thought_repository.save = AsyncMock(return_value=saved_thought)
        entity_extraction_service.extract_entities = AsyncMock(return_value=[])
        semantic_entry_repository.save_many = AsyncMock(return_value=[])

        # Act
        result = await use_case.execute(
            user_id=user_id,
            content=content,
        )

        # Assert
        assert result.user_id == user_id
        assert result.content == content
        assert isinstance(result.metadata, ThoughtMetadata)
        assert len(result.semantic_entries) == 0
        
        thought_repository.save.assert_called_once()
        entity_extraction_service.extract_entities.assert_called_once()
        semantic_entry_repository.save_many.assert_not_called()

    async def test_creates_thought_with_custom_timestamp(
        self, use_case, thought_repository, semantic_entry_repository, entity_extraction_service
    ):
        """Test thought creation with custom timestamp."""
        # Arrange
        user_id = uuid4()
        content = "Thought with custom timestamp"
        custom_timestamp = datetime(2023, 1, 1, 12, 0, 0)
        
        saved_thought = Thought(
            id=uuid4(),
            user_id=user_id,
            content=content,
            timestamp=custom_timestamp,
        )

        thought_repository.save = AsyncMock(return_value=saved_thought)
        entity_extraction_service.extract_entities = AsyncMock(return_value=[])

        # Act
        result = await use_case.execute(
            user_id=user_id,
            content=content,
            timestamp=custom_timestamp,
        )

        # Assert
        assert result.timestamp == custom_timestamp
        thought_repository.save.assert_called_once()

    async def test_handles_entity_extraction_failure(
        self, use_case, thought_repository, semantic_entry_repository, entity_extraction_service
    ):
        """Test handling of entity extraction failure."""
        # Arrange
        user_id = uuid4()
        content = "Test content"
        
        saved_thought = Thought(
            id=uuid4(),
            user_id=user_id,
            content=content,
        )

        thought_repository.save = AsyncMock(return_value=saved_thought)
        entity_extraction_service.extract_entities = AsyncMock(
            side_effect=Exception("LLM service unavailable")
        )

        # Act & Assert
        with pytest.raises(EntityExtractionError) as exc_info:
            await use_case.execute(user_id=user_id, content=content)
        
        assert "Failed to extract entities" in str(exc_info.value)
        assert "LLM service unavailable" in str(exc_info.value)
        
        thought_repository.save.assert_called_once()
        entity_extraction_service.extract_entities.assert_called_once()
        semantic_entry_repository.save_many.assert_not_called()

    async def test_creates_thought_when_no_entities_extracted(
        self, use_case, thought_repository, semantic_entry_repository, entity_extraction_service
    ):
        """Test thought creation when no entities are extracted."""
        # Arrange
        user_id = uuid4()
        content = "Simple content with no entities"
        
        saved_thought = Thought(
            id=uuid4(),
            user_id=user_id,
            content=content,
        )

        thought_repository.save = AsyncMock(return_value=saved_thought)
        entity_extraction_service.extract_entities = AsyncMock(return_value=[])

        # Act
        result = await use_case.execute(user_id=user_id, content=content)

        # Assert
        assert result.user_id == user_id
        assert result.content == content
        assert len(result.semantic_entries) == 0
        
        thought_repository.save.assert_called_once()
        entity_extraction_service.extract_entities.assert_called_once()
        semantic_entry_repository.save_many.assert_not_called()

    async def test_validates_empty_content_through_domain_model(self, use_case):
        """Test that empty content validation is handled by domain model."""
        # Arrange
        user_id = uuid4()
        empty_content = "   "  # Whitespace only

        # Act & Assert
        # This should be caught by the Thought domain model validation
        with pytest.raises(ValueError) as exc_info:
            await use_case.execute(user_id=user_id, content=empty_content)
        
        assert "Thought content cannot be empty" in str(exc_info.value)