"""Tests for DeleteThoughtUseCase."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.application.usecases.delete_thought_usecase import DeleteThoughtUseCase
from src.domain.entities.thought import Thought, ThoughtMetadata
from src.domain.exceptions import ThoughtNotFoundError
from src.domain.repositories.semantic_entry_repository import SemanticEntryRepository
from src.domain.repositories.thought_repository import ThoughtRepository


class TestDeleteThoughtUseCase:
    """Test cases for DeleteThoughtUseCase."""

    @pytest.fixture
    def thought_repository(self):
        """Mock thought repository."""
        return Mock(spec=ThoughtRepository)

    @pytest.fixture
    def semantic_entry_repository(self):
        """Mock semantic entry repository."""
        return Mock(spec=SemanticEntryRepository)

    @pytest.fixture
    def use_case(self, thought_repository, semantic_entry_repository):
        """Create use case instance with mocked dependencies."""
        return DeleteThoughtUseCase(
            thought_repository=thought_repository,
            semantic_entry_repository=semantic_entry_repository,
        )

    @pytest.fixture
    def existing_thought(self):
        """Sample existing thought for testing."""
        return Thought(
            id=uuid4(),
            user_id=uuid4(),
            content="Thought to be deleted",
            timestamp=datetime(2023, 1, 1, 10, 0, 0),
            metadata=ThoughtMetadata(),
        )

    async def test_deletes_thought_and_semantic_entries_successfully(
        self, use_case, thought_repository, semantic_entry_repository, existing_thought
    ):
        """Test successful deletion of thought and its semantic entries."""
        # Arrange
        thought_repository.find_by_id = AsyncMock(return_value=existing_thought)
        semantic_entry_repository.delete_by_thought = AsyncMock()
        thought_repository.delete = AsyncMock()

        # Act
        await use_case.execute(
            thought_id=existing_thought.id,
            user_id=existing_thought.user_id,
        )

        # Assert
        thought_repository.find_by_id.assert_called_once_with(existing_thought.id)
        semantic_entry_repository.delete_by_thought.assert_called_once_with(existing_thought.id)
        thought_repository.delete.assert_called_once_with(existing_thought.id)

    async def test_raises_error_when_thought_not_found(
        self, use_case, thought_repository, semantic_entry_repository
    ):
        """Test error handling when thought is not found."""
        # Arrange
        thought_id = uuid4()
        user_id = uuid4()
        thought_repository.find_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(ThoughtNotFoundError) as exc_info:
            await use_case.execute(thought_id=thought_id, user_id=user_id)
        
        assert exc_info.value.thought_id == thought_id
        
        thought_repository.find_by_id.assert_called_once_with(thought_id)
        semantic_entry_repository.delete_by_thought.assert_not_called()
        thought_repository.delete.assert_not_called()

    async def test_raises_error_when_user_not_owner(
        self, use_case, thought_repository, semantic_entry_repository, existing_thought
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
            )
        
        assert "User does not have permission to delete this thought" in str(exc_info.value)
        
        thought_repository.find_by_id.assert_called_once_with(existing_thought.id)
        semantic_entry_repository.delete_by_thought.assert_not_called()
        thought_repository.delete.assert_not_called()

    async def test_deletes_semantic_entries_before_thought(
        self, use_case, thought_repository, semantic_entry_repository, existing_thought
    ):
        """Test that semantic entries are deleted before the thought (referential integrity)."""
        # Arrange
        call_order = []
        
        def track_semantic_delete(*args):
            call_order.append("semantic_entries_deleted")
        
        def track_thought_delete(*args):
            call_order.append("thought_deleted")

        thought_repository.find_by_id = AsyncMock(return_value=existing_thought)
        semantic_entry_repository.delete_by_thought = AsyncMock(side_effect=track_semantic_delete)
        thought_repository.delete = AsyncMock(side_effect=track_thought_delete)

        # Act
        await use_case.execute(
            thought_id=existing_thought.id,
            user_id=existing_thought.user_id,
        )

        # Assert
        assert call_order == ["semantic_entries_deleted", "thought_deleted"]

    async def test_handles_semantic_entry_deletion_failure(
        self, use_case, thought_repository, semantic_entry_repository, existing_thought
    ):
        """Test handling of semantic entry deletion failure."""
        # Arrange
        thought_repository.find_by_id = AsyncMock(return_value=existing_thought)
        semantic_entry_repository.delete_by_thought = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        thought_repository.delete = AsyncMock()

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await use_case.execute(
                thought_id=existing_thought.id,
                user_id=existing_thought.user_id,
            )
        
        assert "Database connection failed" in str(exc_info.value)
        
        thought_repository.find_by_id.assert_called_once_with(existing_thought.id)
        semantic_entry_repository.delete_by_thought.assert_called_once_with(existing_thought.id)
        thought_repository.delete.assert_not_called()  # Should not be called if semantic deletion fails

    async def test_handles_thought_deletion_failure(
        self, use_case, thought_repository, semantic_entry_repository, existing_thought
    ):
        """Test handling of thought deletion failure."""
        # Arrange
        thought_repository.find_by_id = AsyncMock(return_value=existing_thought)
        semantic_entry_repository.delete_by_thought = AsyncMock()
        thought_repository.delete = AsyncMock(
            side_effect=Exception("Database constraint violation")
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await use_case.execute(
                thought_id=existing_thought.id,
                user_id=existing_thought.user_id,
            )
        
        assert "Database constraint violation" in str(exc_info.value)
        
        thought_repository.find_by_id.assert_called_once_with(existing_thought.id)
        semantic_entry_repository.delete_by_thought.assert_called_once_with(existing_thought.id)
        thought_repository.delete.assert_called_once_with(existing_thought.id)