"""Unit tests for thoughts API routes without full app initialization."""

import json
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock

from src.api.routes.thoughts import create_thoughts_router
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


@pytest.fixture
def mock_use_cases():
    """Create mock use cases."""
    return {
        "create_thought_usecase": AsyncMock(),
        "get_thoughts_usecase": AsyncMock(),
        "get_thought_by_id_usecase": AsyncMock(),
        "update_thought_usecase": AsyncMock(),
        "delete_thought_usecase": AsyncMock(),
    }


@pytest.fixture
def mock_auth_middleware(test_user):
    """Create mock authentication middleware."""
    auth_middleware = Mock()
    auth_middleware.require_authentication = AsyncMock(return_value=test_user)
    return auth_middleware


@pytest.fixture
def client(mock_use_cases, mock_auth_middleware):
    """Create a test client with mocked dependencies."""
    app = FastAPI()
    
    thoughts_router = create_thoughts_router(
        create_thought_usecase=mock_use_cases["create_thought_usecase"],
        get_thoughts_usecase=mock_use_cases["get_thoughts_usecase"],
        get_thought_by_id_usecase=mock_use_cases["get_thought_by_id_usecase"],
        update_thought_usecase=mock_use_cases["update_thought_usecase"],
        delete_thought_usecase=mock_use_cases["delete_thought_usecase"],
        auth_middleware=mock_auth_middleware,
    )
    
    app.include_router(thoughts_router)
    return TestClient(app)


class TestCreateThought:
    """Tests for POST /api/v1/thoughts endpoint."""

    async def test_create_thought_success(self, client, mock_use_cases, test_user, test_thought):
        """Test successful thought creation."""
        mock_use_cases["create_thought_usecase"].execute.return_value = test_thought

        request_data = {
            "content": "This is a test thought about my day in New York.",
            "metadata": {
                "location": {"latitude": 40.7128, "longitude": -74.0060, "name": "New York"},
                "weather": {"temperature": 20.0, "condition": "sunny"},
                "mood": "happy",
                "tags": ["work", "travel"],
                "custom": {"source": "mobile"},
            },
        }

        response = client.post(
            "/api/v1/thoughts",
            json=request_data,
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["content"] == test_thought.content
        assert data["metadata"]["location"]["name"] == "New York"
        assert len(data["semantic_entries"]) == 1
        assert data["semantic_entries"][0]["entity_value"] == "New York"

        # Verify use case was called correctly
        mock_use_cases["create_thought_usecase"].execute.assert_called_once()
        call_args = mock_use_cases["create_thought_usecase"].execute.call_args
        assert call_args[1]["user_id"] == test_user.id
        assert call_args[1]["content"] == request_data["content"]

    async def test_create_thought_entity_extraction_error(self, client, mock_use_cases):
        """Test thought creation with entity extraction failure."""
        mock_use_cases["create_thought_usecase"].execute.side_effect = EntityExtractionError("LLM service unavailable")

        request_data = {"content": "Test thought"}

        response = client.post(
            "/api/v1/thoughts",
            json=request_data,
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 422
        assert "Entity extraction failed" in response.json()["detail"]

    async def test_create_thought_invalid_content(self, client):
        """Test thought creation with invalid content."""
        request_data = {"content": ""}  # Empty content

        response = client.post(
            "/api/v1/thoughts",
            json=request_data,
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 422  # Pydantic validation error


class TestGetThoughts:
    """Tests for GET /api/v1/thoughts endpoint."""

    async def test_get_thoughts_success(self, client, mock_use_cases, test_user, test_thought):
        """Test successful thoughts retrieval."""
        mock_use_cases["get_thoughts_usecase"].execute.return_value = [test_thought]

        response = client.get(
            "/api/v1/thoughts",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["thoughts"]) == 1
        assert data["thoughts"][0]["content"] == test_thought.content
        assert data["total"] == 1
        assert data["skip"] == 0
        assert data["limit"] == 100

        mock_use_cases["get_thoughts_usecase"].execute.assert_called_once_with(
            user_id=test_user.id, skip=0, limit=100
        )

    async def test_get_thoughts_with_pagination(self, client, mock_use_cases, test_user):
        """Test thoughts retrieval with pagination parameters."""
        mock_use_cases["get_thoughts_usecase"].execute.return_value = []

        response = client.get(
            "/api/v1/thoughts?skip=10&limit=50",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 10
        assert data["limit"] == 50

        mock_use_cases["get_thoughts_usecase"].execute.assert_called_once_with(
            user_id=test_user.id, skip=10, limit=50
        )

    async def test_get_thoughts_invalid_pagination(self, client, mock_use_cases):
        """Test thoughts retrieval with invalid pagination parameters."""
        mock_use_cases["get_thoughts_usecase"].execute.side_effect = ValueError("Skip parameter must be non-negative")

        response = client.get(
            "/api/v1/thoughts?skip=-1",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 400
        assert "Skip parameter must be non-negative" in response.json()["detail"]


class TestGetThoughtById:
    """Tests for GET /api/v1/thoughts/{id} endpoint."""

    async def test_get_thought_by_id_success(self, client, mock_use_cases, test_user, test_thought):
        """Test successful thought retrieval by ID."""
        mock_use_cases["get_thought_by_id_usecase"].execute.return_value = test_thought

        response = client.get(
            f"/api/v1/thoughts/{test_thought.id}",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_thought.id)
        assert data["content"] == test_thought.content
        assert len(data["semantic_entries"]) == 1

        mock_use_cases["get_thought_by_id_usecase"].execute.assert_called_once_with(
            thought_id=test_thought.id, user_id=test_user.id
        )

    async def test_get_thought_by_id_not_found(self, client, mock_use_cases):
        """Test thought retrieval for non-existent thought."""
        thought_id = uuid4()
        mock_use_cases["get_thought_by_id_usecase"].execute.side_effect = ThoughtNotFoundError(thought_id)

        response = client.get(
            f"/api/v1/thoughts/{thought_id}",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 404
        assert "Thought not found" in response.json()["detail"]

    async def test_get_thought_by_id_access_denied(self, client, mock_use_cases):
        """Test thought retrieval with access denied."""
        thought_id = uuid4()
        mock_use_cases["get_thought_by_id_usecase"].execute.side_effect = ValueError("User does not have permission to access this thought")

        response = client.get(
            f"/api/v1/thoughts/{thought_id}",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]


class TestUpdateThought:
    """Tests for PUT /api/v1/thoughts/{id} endpoint."""

    async def test_update_thought_success(self, client, mock_use_cases, test_user, test_thought):
        """Test successful thought update."""
        updated_thought = test_thought.model_copy(
            update={"content": "Updated content", "updated_at": datetime.now()}
        )
        
        mock_use_cases["update_thought_usecase"].execute.return_value = updated_thought

        request_data = {
            "content": "Updated content",
            "metadata": {"mood": "excited"},
        }

        response = client.put(
            f"/api/v1/thoughts/{test_thought.id}",
            json=request_data,
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Updated content"

        mock_use_cases["update_thought_usecase"].execute.assert_called_once()
        call_args = mock_use_cases["update_thought_usecase"].execute.call_args
        assert call_args[1]["thought_id"] == test_thought.id
        assert call_args[1]["user_id"] == test_user.id
        assert call_args[1]["content"] == "Updated content"

    async def test_update_thought_not_found(self, client, mock_use_cases):
        """Test thought update for non-existent thought."""
        thought_id = uuid4()
        mock_use_cases["update_thought_usecase"].execute.side_effect = ThoughtNotFoundError(thought_id)

        request_data = {"content": "Updated content"}

        response = client.put(
            f"/api/v1/thoughts/{thought_id}",
            json=request_data,
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 404
        assert "Thought not found" in response.json()["detail"]

    async def test_update_thought_entity_extraction_error(self, client, mock_use_cases, test_thought):
        """Test thought update with entity extraction failure."""
        mock_use_cases["update_thought_usecase"].execute.side_effect = EntityExtractionError("LLM service unavailable")

        request_data = {"content": "Updated content"}

        response = client.put(
            f"/api/v1/thoughts/{test_thought.id}",
            json=request_data,
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 422
        assert "Entity extraction failed" in response.json()["detail"]


class TestDeleteThought:
    """Tests for DELETE /api/v1/thoughts/{id} endpoint."""

    async def test_delete_thought_success(self, client, mock_use_cases, test_thought):
        """Test successful thought deletion."""
        mock_use_cases["delete_thought_usecase"].execute.return_value = None

        response = client.delete(
            f"/api/v1/thoughts/{test_thought.id}",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 204
        assert response.content == b""

        mock_use_cases["delete_thought_usecase"].execute.assert_called_once_with(
            thought_id=test_thought.id, user_id=test_user.id
        )

    async def test_delete_thought_not_found(self, client, mock_use_cases):
        """Test thought deletion for non-existent thought."""
        thought_id = uuid4()
        mock_use_cases["delete_thought_usecase"].execute.side_effect = ThoughtNotFoundError(thought_id)

        response = client.delete(
            f"/api/v1/thoughts/{thought_id}",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 404
        assert "Thought not found" in response.json()["detail"]

    async def test_delete_thought_access_denied(self, client, mock_use_cases):
        """Test thought deletion with access denied."""
        thought_id = uuid4()
        mock_use_cases["delete_thought_usecase"].execute.side_effect = ValueError("User does not have permission to delete this thought")

        response = client.delete(
            f"/api/v1/thoughts/{thought_id}",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]