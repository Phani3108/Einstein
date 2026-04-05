"""Simple tests for thoughts API endpoints logic."""

import json
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from unittest.mock import AsyncMock, Mock

from src.api.models.thought_models import (
    CreateThoughtRequest,
    ThoughtResponse,
    UpdateThoughtRequest,
)
from src.domain.entities.thought import Thought, ThoughtMetadata, GeoLocation, WeatherData
from src.domain.entities.semantic_entry import SemanticEntry
from src.domain.entities.enums import EntityType
from src.domain.entities.user import User
from src.domain.exceptions import ThoughtNotFoundError, EntityExtractionError


@pytest.fixture
def test_user():
    """Create a test user."""
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        is_admin=False,
    )


@pytest.fixture
def test_thought(test_user):
    """Create a test thought."""
    return Thought(
        id=uuid4(),
        user_id=test_user.id,
        content="This is a test thought about my day in New York.",
        timestamp=datetime(2024, 1, 15, 10, 30, 0),
        metadata=ThoughtMetadata(
            location=GeoLocation(latitude=40.7128, longitude=-74.0060, name="New York"),
            weather=WeatherData(temperature=20.0, condition="sunny"),
            mood="happy",
            tags=["work", "travel"],
            custom={"source": "mobile"},
        ),
        semantic_entries=[
            SemanticEntry(
                id=uuid4(),
                thought_id=uuid4(),
                entity_type=EntityType.LOCATION,
                entity_value="New York",
                confidence=0.95,
                context="my day in New York",
                extracted_at=datetime.now(),
            )
        ],
    )


class TestThoughtModels:
    """Tests for thought API models."""

    def test_create_thought_request_validation(self):
        """Test CreateThoughtRequest validation."""
        # Valid request
        request = CreateThoughtRequest(
            content="Test thought",
            metadata={
                "location": {"latitude": 40.7128, "longitude": -74.0060, "name": "New York"},
                "mood": "happy",
                "tags": ["test"],
            },
        )
        assert request.content == "Test thought"
        assert request.metadata.location.name == "New York"
        assert request.metadata.mood == "happy"
        assert "test" in request.metadata.tags

        # Invalid request - empty content
        with pytest.raises(ValueError):
            CreateThoughtRequest(content="")

    def test_update_thought_request_validation(self):
        """Test UpdateThoughtRequest validation."""
        # Valid request
        request = UpdateThoughtRequest(
            content="Updated thought",
            metadata={"mood": "excited"},
        )
        assert request.content == "Updated thought"
        assert request.metadata.mood == "excited"

        # Valid request - partial update
        request = UpdateThoughtRequest(content="Updated content only")
        assert request.content == "Updated content only"
        assert request.metadata is None

        # Invalid request - empty content
        with pytest.raises(ValueError):
            UpdateThoughtRequest(content="")

    def test_thought_response_from_domain(self, test_thought):
        """Test ThoughtResponse creation from domain object."""
        response = ThoughtResponse.from_domain(test_thought)
        
        assert response.id == test_thought.id
        assert response.content == test_thought.content
        assert response.timestamp == test_thought.timestamp
        assert response.metadata.location.name == "New York"
        assert response.metadata.mood == "happy"
        assert len(response.semantic_entries) == 1
        assert response.semantic_entries[0].entity_value == "New York"
        assert response.semantic_entries[0].entity_type == "location"

    def test_metadata_conversion(self):
        """Test metadata conversion between request and domain models."""
        from src.api.models.thought_models import ThoughtMetadataRequest
        
        request_metadata = ThoughtMetadataRequest(
            location={"latitude": 40.7128, "longitude": -74.0060, "name": "New York"},
            weather={"temperature": 20.0, "condition": "sunny"},
            mood="happy",
            tags=["work", "travel"],
            custom={"source": "mobile"},
        )
        
        domain_metadata = request_metadata.to_domain()
        
        assert domain_metadata.location.latitude == 40.7128
        assert domain_metadata.location.longitude == -74.0060
        assert domain_metadata.location.name == "New York"
        assert domain_metadata.weather.temperature == 20.0
        assert domain_metadata.weather.condition == "sunny"
        assert domain_metadata.mood == "happy"
        assert domain_metadata.tags == ["work", "travel"]
        assert domain_metadata.custom == {"source": "mobile"}


class TestThoughtRouteLogic:
    """Tests for thought route business logic."""

    async def test_create_thought_success_logic(self, test_user, test_thought):
        """Test the logic of creating a thought successfully."""
        # Mock use case
        create_usecase = AsyncMock()
        create_usecase.execute.return_value = test_thought

        # Mock auth middleware
        auth_middleware = Mock()
        auth_middleware.require_authentication = AsyncMock(return_value=test_user)

        # Simulate the route logic
        request_data = CreateThoughtRequest(
            content="This is a test thought about my day in New York.",
            metadata={
                "location": {"latitude": 40.7128, "longitude": -74.0060, "name": "New York"},
                "weather": {"temperature": 20.0, "condition": "sunny"},
                "mood": "happy",
                "tags": ["work", "travel"],
                "custom": {"source": "mobile"},
            },
        )

        # Execute the logic that would be in the route
        metadata = request_data.metadata.to_domain() if request_data.metadata else None
        
        result = await create_usecase.execute(
            user_id=test_user.id,
            content=request_data.content,
            metadata=metadata,
            timestamp=request_data.timestamp,
        )

        response = ThoughtResponse.from_domain(result)

        # Assertions
        assert response.content == test_thought.content
        assert response.metadata.location.name == "New York"
        assert len(response.semantic_entries) == 1
        assert response.semantic_entries[0].entity_value == "New York"

        # Verify use case was called correctly
        create_usecase.execute.assert_called_once()
        call_args = create_usecase.execute.call_args
        assert call_args[1]["user_id"] == test_user.id
        assert call_args[1]["content"] == request_data.content

    async def test_create_thought_entity_extraction_error_logic(self, test_user):
        """Test the logic of handling entity extraction errors."""
        # Mock use case with error
        create_usecase = AsyncMock()
        create_usecase.execute.side_effect = EntityExtractionError("LLM service unavailable")

        # Mock auth middleware
        auth_middleware = Mock()
        auth_middleware.require_authentication = AsyncMock(return_value=test_user)

        request_data = CreateThoughtRequest(content="Test thought")

        # Execute the logic that would be in the route
        with pytest.raises(EntityExtractionError) as exc_info:
            await create_usecase.execute(
                user_id=test_user.id,
                content=request_data.content,
                metadata=None,
                timestamp=request_data.timestamp,
            )

        assert "LLM service unavailable" in str(exc_info.value)

    async def test_get_thoughts_success_logic(self, test_user, test_thought):
        """Test the logic of getting thoughts successfully."""
        # Mock use case
        get_usecase = AsyncMock()
        get_usecase.execute.return_value = [test_thought]

        # Mock auth middleware
        auth_middleware = Mock()
        auth_middleware.require_authentication = AsyncMock(return_value=test_user)

        # Execute the logic that would be in the route
        thoughts = await get_usecase.execute(
            user_id=test_user.id,
            skip=0,
            limit=100,
        )

        # Create response
        from src.api.models.thought_models import ThoughtListResponse
        response = ThoughtListResponse.from_domain_list(
            thoughts=thoughts,
            total=len(thoughts),
            skip=0,
            limit=100,
        )

        # Assertions
        assert len(response.thoughts) == 1
        assert response.thoughts[0].content == test_thought.content
        assert response.total == 1
        assert response.skip == 0
        assert response.limit == 100

        get_usecase.execute.assert_called_once_with(
            user_id=test_user.id, skip=0, limit=100
        )

    async def test_get_thought_by_id_success_logic(self, test_user, test_thought):
        """Test the logic of getting a thought by ID successfully."""
        # Mock use case
        get_usecase = AsyncMock()
        get_usecase.execute.return_value = test_thought

        # Mock auth middleware
        auth_middleware = Mock()
        auth_middleware.require_authentication = AsyncMock(return_value=test_user)

        # Execute the logic that would be in the route
        thought = await get_usecase.execute(
            thought_id=test_thought.id,
            user_id=test_user.id,
        )

        response = ThoughtResponse.from_domain(thought)

        # Assertions
        assert response.id == test_thought.id
        assert response.content == test_thought.content
        assert len(response.semantic_entries) == 1

        get_usecase.execute.assert_called_once_with(
            thought_id=test_thought.id, user_id=test_user.id
        )

    async def test_get_thought_by_id_not_found_logic(self, test_user):
        """Test the logic of handling thought not found."""
        # Mock use case with error
        get_usecase = AsyncMock()
        thought_id = uuid4()
        get_usecase.execute.side_effect = ThoughtNotFoundError(thought_id)

        # Mock auth middleware
        auth_middleware = Mock()
        auth_middleware.require_authentication = AsyncMock(return_value=test_user)

        # Execute the logic that would be in the route
        with pytest.raises(ThoughtNotFoundError):
            await get_usecase.execute(
                thought_id=thought_id,
                user_id=test_user.id,
            )

    async def test_update_thought_success_logic(self, test_user, test_thought):
        """Test the logic of updating a thought successfully."""
        # Mock use case
        update_usecase = AsyncMock()
        updated_thought = test_thought.model_copy(
            update={"content": "Updated content", "updated_at": datetime.now()}
        )
        update_usecase.execute.return_value = updated_thought

        # Mock auth middleware
        auth_middleware = Mock()
        auth_middleware.require_authentication = AsyncMock(return_value=test_user)

        request_data = UpdateThoughtRequest(
            content="Updated content",
            metadata={"mood": "excited"},
        )

        # Execute the logic that would be in the route
        metadata = request_data.metadata.to_domain() if request_data.metadata else None
        
        thought = await update_usecase.execute(
            thought_id=test_thought.id,
            user_id=test_user.id,
            content=request_data.content,
            metadata=metadata,
        )

        response = ThoughtResponse.from_domain(thought)

        # Assertions
        assert response.content == "Updated content"

        update_usecase.execute.assert_called_once()
        call_args = update_usecase.execute.call_args
        assert call_args[1]["thought_id"] == test_thought.id
        assert call_args[1]["user_id"] == test_user.id
        assert call_args[1]["content"] == "Updated content"

    async def test_delete_thought_success_logic(self, test_user, test_thought):
        """Test the logic of deleting a thought successfully."""
        # Mock use case
        delete_usecase = AsyncMock()
        delete_usecase.execute.return_value = None

        # Mock auth middleware
        auth_middleware = Mock()
        auth_middleware.require_authentication = AsyncMock(return_value=test_user)

        # Execute the logic that would be in the route
        await delete_usecase.execute(
            thought_id=test_thought.id,
            user_id=test_user.id,
        )

        delete_usecase.execute.assert_called_once_with(
            thought_id=test_thought.id, user_id=test_user.id
        )

    async def test_delete_thought_not_found_logic(self, test_user):
        """Test the logic of handling thought deletion when not found."""
        # Mock use case with error
        delete_usecase = AsyncMock()
        thought_id = uuid4()
        delete_usecase.execute.side_effect = ThoughtNotFoundError(thought_id)

        # Mock auth middleware
        auth_middleware = Mock()
        auth_middleware.require_authentication = AsyncMock(return_value=test_user)

        # Execute the logic that would be in the route
        with pytest.raises(ThoughtNotFoundError):
            await delete_usecase.execute(
                thought_id=thought_id,
                user_id=test_user.id,
            )