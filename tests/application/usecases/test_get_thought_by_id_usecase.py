"""Tests for GetThoughtByIdUseCase."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.application.usecases.get_thought_by_id_usecase import GetThoughtByIdUseCase
from src.domain.entities.thought import Thought, ThoughtMetadata
from src.domain.exceptions import ThoughtNotFoundError
from src.domain.repositories.thought_repository import ThoughtRepository


class TestGetThoughtByIdUseCase:
    """Test cases for GetThoughtByIdUseCase."""

    @pytest.fixture
    def thought_repository(self):
        """Mock thought repository."""
        return Mock(spec=ThoughtRepository)

    @pytest.fixture
    def use_case(self, thought_repository):
        """Create use case instance with mocked dependencies."""
        return GetThoughtByIdUseCase(thought_repository=thought_repository)

    @pytest.fixture
    def sample_thought(self):
        """Sample thought for testing."""
        return Thought(
            id=uuid4(),
            user_id=uuid4(),
            content="Sample thought content",
            timestamp=datetime(2023, 1, 1, 10, 0, 0),
            metadata=ThoughtMetadata(),
        )

    async def test_gets_thought_by_id_successfully(
        self, use_case, thought_repository, sample_thought
    ):
        """Test successful retrieval of thought by ID."""
        # Arrange
        thought_repository.find_by_id = AsyncMock(return_value=sample_thought)

        # Act
        result = await use_case.execute(
            thought_id=sample_thought.id,
            user_id=sample_thought.user_id,
        )

        # Assert
        assert result == sample_thought
        thought_repository.find_by_id.assert_called_once_with(sample_thought.id)

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
            await use_case.execute(thought_id=thought_id, user_id=user_id)
        
        assert exc_info.value.thought_id == thought_id
        thought_repository.find_by_id.assert_called_once_with(thought_id)

    async def test_raises_error_when_user_not_owner(
        self, use_case, thought_repository, sample_thought
    ):
        """Test error handling when user is not the owner."""
        # Arrange
        different_user_id = uuid4()
        thought_repository.find_by_id = AsyncMock(return_value=sample_thought)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await use_case.execute(
                thought_id=sample_thought.id,
                user_id=different_user_id,
            )
        
        assert "User does not have permission to access this thought" in str(exc_info.value)
        thought_repository.find_by_id.assert_called_once_with(sample_thought.id)

    async def test_verifies_ownership_before_returning_thought(
        self, use_case, thought_repository, sample_thought
    ):
        """Test that ownership is verified before returning the thought."""
        # Arrange
        thought_repository.find_by_id = AsyncMock(return_value=sample_thought)

        # Act
        result = await use_case.execute(
            thought_id=sample_thought.id,
            user_id=sample_thought.user_id,
        )

        # Assert
        assert result.user_id == sample_thought.user_id
        thought_repository.find_by_id.assert_called_once_with(sample_thought.id)