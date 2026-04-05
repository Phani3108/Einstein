"""Tests for GetThoughtsUseCase."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.application.usecases.get_thoughts_usecase import GetThoughtsUseCase
from src.domain.entities.thought import Thought, ThoughtMetadata
from src.domain.repositories.thought_repository import ThoughtRepository


class TestGetThoughtsUseCase:
    """Test cases for GetThoughtsUseCase."""

    @pytest.fixture
    def thought_repository(self):
        """Mock thought repository."""
        return Mock(spec=ThoughtRepository)

    @pytest.fixture
    def use_case(self, thought_repository):
        """Create use case instance with mocked dependencies."""
        return GetThoughtsUseCase(thought_repository=thought_repository)

    @pytest.fixture
    def sample_thoughts(self):
        """Sample thoughts for testing."""
        user_id = uuid4()
        return [
            Thought(
                id=uuid4(),
                user_id=user_id,
                content="First thought",
                timestamp=datetime(2023, 1, 1, 10, 0, 0),
            ),
            Thought(
                id=uuid4(),
                user_id=user_id,
                content="Second thought",
                timestamp=datetime(2023, 1, 1, 11, 0, 0),
            ),
            Thought(
                id=uuid4(),
                user_id=user_id,
                content="Third thought",
                timestamp=datetime(2023, 1, 1, 12, 0, 0),
            ),
        ]

    @pytest.mark.asyncio
    async def test_gets_thoughts_with_default_pagination(
        self, use_case, thought_repository, sample_thoughts
    ):
        """Test getting thoughts with default pagination parameters."""
        # Arrange
        user_id = uuid4()
        thought_repository.find_by_user = AsyncMock(return_value=sample_thoughts)

        # Act
        result = await use_case.execute(user_id=user_id)

        # Assert
        assert result == sample_thoughts
        thought_repository.find_by_user.assert_called_once_with(
            user_id=user_id, skip=0, limit=100
        )

    async def test_gets_thoughts_with_custom_pagination(
        self, use_case, thought_repository, sample_thoughts
    ):
        """Test getting thoughts with custom pagination parameters."""
        # Arrange
        user_id = uuid4()
        skip = 10
        limit = 50
        thought_repository.find_by_user = AsyncMock(return_value=sample_thoughts[:2])

        # Act
        result = await use_case.execute(user_id=user_id, skip=skip, limit=limit)

        # Assert
        assert len(result) == 2
        thought_repository.find_by_user.assert_called_once_with(
            user_id=user_id, skip=skip, limit=limit
        )

    async def test_gets_empty_list_when_no_thoughts_found(
        self, use_case, thought_repository
    ):
        """Test getting empty list when user has no thoughts."""
        # Arrange
        user_id = uuid4()
        thought_repository.find_by_user = AsyncMock(return_value=[])

        # Act
        result = await use_case.execute(user_id=user_id)

        # Assert
        assert result == []
        thought_repository.find_by_user.assert_called_once_with(
            user_id=user_id, skip=0, limit=100
        )

    async def test_validates_negative_skip_parameter(self, use_case):
        """Test validation of negative skip parameter."""
        # Arrange
        user_id = uuid4()
        negative_skip = -1

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await use_case.execute(user_id=user_id, skip=negative_skip)
        
        assert "Skip parameter must be non-negative" in str(exc_info.value)

    async def test_validates_zero_limit_parameter(self, use_case):
        """Test validation of zero limit parameter."""
        # Arrange
        user_id = uuid4()
        zero_limit = 0

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await use_case.execute(user_id=user_id, limit=zero_limit)
        
        assert "Limit parameter must be positive" in str(exc_info.value)

    async def test_validates_negative_limit_parameter(self, use_case):
        """Test validation of negative limit parameter."""
        # Arrange
        user_id = uuid4()
        negative_limit = -10

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await use_case.execute(user_id=user_id, limit=negative_limit)
        
        assert "Limit parameter must be positive" in str(exc_info.value)

    async def test_validates_excessive_limit_parameter(self, use_case):
        """Test validation of excessive limit parameter."""
        # Arrange
        user_id = uuid4()
        excessive_limit = 1001

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await use_case.execute(user_id=user_id, limit=excessive_limit)
        
        assert "Limit parameter cannot exceed 1000" in str(exc_info.value)

    async def test_accepts_maximum_allowed_limit(
        self, use_case, thought_repository, sample_thoughts
    ):
        """Test that maximum allowed limit (1000) is accepted."""
        # Arrange
        user_id = uuid4()
        max_limit = 1000
        thought_repository.find_by_user = AsyncMock(return_value=sample_thoughts)

        # Act
        result = await use_case.execute(user_id=user_id, limit=max_limit)

        # Assert
        assert result == sample_thoughts
        thought_repository.find_by_user.assert_called_once_with(
            user_id=user_id, skip=0, limit=max_limit
        )

    async def test_accepts_zero_skip_parameter(
        self, use_case, thought_repository, sample_thoughts
    ):
        """Test that zero skip parameter is accepted."""
        # Arrange
        user_id = uuid4()
        zero_skip = 0
        thought_repository.find_by_user = AsyncMock(return_value=sample_thoughts)

        # Act
        result = await use_case.execute(user_id=user_id, skip=zero_skip)

        # Assert
        assert result == sample_thoughts
        thought_repository.find_by_user.assert_called_once_with(
            user_id=user_id, skip=zero_skip, limit=100
        )