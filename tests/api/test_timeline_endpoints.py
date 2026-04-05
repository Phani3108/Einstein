"""Integration tests for timeline API endpoints."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.timeline import create_timeline_router
from src.domain.entities.enums import EntityType
from src.domain.entities.timeline import (
    DateRange,
    EntityConnection,
    TimelineEntry,
    TimelineResponse,
    TimelineSummary,
)
from src.domain.entities.thought import Thought, ThoughtMetadata
from src.domain.entities.user import User
from src.domain.exceptions import TimelineError, TimelineQueryError


@pytest.fixture
def mock_container():
    """Create a mock container with timeline dependencies."""
    container = Mock()
    
    # Mock timeline use case
    timeline_usecase = AsyncMock()
    container.get_timeline_usecase.return_value = timeline_usecase
    
    # Mock auth middleware
    auth_middleware = AsyncMock()
    container.auth_middleware.return_value = auth_middleware
    
    return container, timeline_usecase, auth_middleware


@pytest.fixture
def test_user():
    """Create a test user."""
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_timeline_entry():
    """Create a sample timeline entry for testing."""
    thought = Thought(
        id=uuid4(),
        user_id=uuid4(),
        content="I went to the park today and felt happy",
        timestamp=datetime.now(),
        metadata=ThoughtMetadata(),
        semantic_entries=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    
    connection = EntityConnection(
        entity_id=uuid4(),
        entity_type=EntityType.LOCATION,
        entity_value="park",
        confidence=0.9,
    )
    
    return TimelineEntry(
        id=thought.id,
        thought=thought,
        timestamp=thought.timestamp,
        entities=[],
        connections=[connection],
        grouped_with=[],
        data_source="thought",
    )


@pytest.fixture
def sample_timeline_response(sample_timeline_entry):
    """Create a sample timeline response."""
    return TimelineResponse(
        entries=[sample_timeline_entry],
        groups=[],
        total_count=1,
        page=1,
        page_size=20,
        has_next=False,
        has_previous=False,
    )


@pytest.fixture
def sample_timeline_summary():
    """Create a sample timeline summary."""
    return TimelineSummary(
        total_entries=10,
        date_range=DateRange(
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
        ),
        entity_counts={"location": 5, "emotion": 3, "person": 2},
        most_active_periods=[
            {"date": "2024-01-15", "count": "3"},
            {"date": "2024-01-14", "count": "2"},
        ],
        top_entities=[
            {"entity_value": "park", "entity_type": "location", "count": "3"},
            {"entity_value": "happy", "entity_type": "emotion", "count": "2"},
        ],
    )


class TestTimelineEndpoints:
    """Test cases for timeline API endpoints."""

    def _create_test_app(self, timeline_usecase, auth_middleware):
        """Create a test FastAPI app with mocked dependencies."""
        app = FastAPI()
        timeline_router = create_timeline_router(
            get_timeline_usecase=timeline_usecase,
            auth_middleware=auth_middleware,
        )
        app.include_router(timeline_router)
        return app

    def test_get_timeline_success(self, mock_container, test_user, sample_timeline_response):
        """Test successful timeline retrieval."""
        container, timeline_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        timeline_usecase.execute.return_value = sample_timeline_response
        
        # Create app with mocked dependencies
        app = self._create_test_app(timeline_usecase, auth_middleware)
        client = TestClient(app)
        
        # Make request
        response = client.get(
            "/api/v1/timeline",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_count"] == 1
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["entries"]) == 1
        assert data["has_next"] is False
        assert data["has_previous"] is False

    def test_get_timeline_with_filters(self, mock_container, test_user, sample_timeline_response):
        """Test timeline retrieval with filters."""
        container, timeline_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        timeline_usecase.execute.return_value = sample_timeline_response
        
        # Create app with mocked dependencies
        app = self._create_test_app(timeline_usecase, auth_middleware)
        client = TestClient(app)
        
        # Make request with filters
        response = client.get(
            "/api/v1/timeline?"
            "start_date=2024-01-01T00:00:00Z&"
            "end_date=2024-12-31T23:59:59Z&"
            "entity_types=location&"
            "entity_types=emotion&"
            "tags=work&"
            "page=1&"
            "page_size=10&"
            "sort_order=desc",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        
        # Verify the use case was called with correct parameters
        timeline_usecase.execute.assert_called_once()
        call_args = timeline_usecase.execute.call_args
        assert call_args[1]["user_id"] == test_user.id
        assert call_args[1]["page"] == 1
        assert call_args[1]["page_size"] == 10
        assert call_args[1]["sort_order"] == "desc"

    def test_get_timeline_invalid_date_format(self, mock_container, test_user):
        """Test timeline with invalid date format."""
        container, timeline_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        
        # Create app with mocked dependencies
        app = self._create_test_app(timeline_usecase, auth_middleware)
        client = TestClient(app)
        
        # Make request with invalid date
        response = client.get(
            "/api/v1/timeline?start_date=invalid-date",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "Invalid start_date format" in data["detail"]

    def test_get_timeline_query_error(self, mock_container, test_user):
        """Test timeline with query parsing error."""
        container, timeline_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        timeline_usecase.execute.side_effect = TimelineQueryError("Invalid query parameters")
        
        # Create app with mocked dependencies
        app = self._create_test_app(timeline_usecase, auth_middleware)
        client = TestClient(app)
        
        # Make request
        response = client.get(
            "/api/v1/timeline",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 422
        data = response.json()
        assert "Timeline query parsing failed" in data["detail"]

    def test_get_timeline_error(self, mock_container, test_user):
        """Test timeline with general error."""
        container, timeline_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        timeline_usecase.execute.side_effect = TimelineError("Timeline service unavailable")
        
        # Create app with mocked dependencies
        app = self._create_test_app(timeline_usecase, auth_middleware)
        client = TestClient(app)
        
        # Make request
        response = client.get(
            "/api/v1/timeline",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "Timeline retrieval failed" in data["detail"]

    def test_get_timeline_unauthorized(self, mock_container):
        """Test timeline without authentication."""
        container, timeline_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.side_effect = Exception("Unauthorized")
        
        # Create app with mocked dependencies
        app = self._create_test_app(timeline_usecase, auth_middleware)
        client = TestClient(app)
        
        # Make request without auth header
        response = client.get("/api/v1/timeline")
        
        # Assertions
        assert response.status_code == 500  # Exception handling

    def test_get_timeline_summary_success(self, mock_container, test_user, sample_timeline_summary):
        """Test successful timeline summary retrieval."""
        container, timeline_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        timeline_usecase.get_summary.return_value = sample_timeline_summary
        
        # Create app with mocked dependencies
        app = self._create_test_app(timeline_usecase, auth_middleware)
        client = TestClient(app)
        
        # Make request
        response = client.get(
            "/api/v1/timeline/summary",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_entries"] == 10
        assert "date_range" in data
        assert "entity_counts" in data
        assert data["entity_counts"]["location"] == 5
        assert len(data["most_active_periods"]) == 2
        assert len(data["top_entities"]) == 2

    def test_get_timeline_summary_error(self, mock_container, test_user):
        """Test timeline summary with error."""
        container, timeline_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        timeline_usecase.get_summary.side_effect = TimelineError("Summary generation failed")
        
        # Create app with mocked dependencies
        app = self._create_test_app(timeline_usecase, auth_middleware)
        client = TestClient(app)
        
        # Make request
        response = client.get(
            "/api/v1/timeline/summary",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "Timeline summary generation failed" in data["detail"]

    def test_get_related_entries_success(self, mock_container, test_user, sample_timeline_entry):
        """Test successful related entries retrieval."""
        container, timeline_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        timeline_usecase.get_related_entries.return_value = [sample_timeline_entry]
        
        # Create app with mocked dependencies
        app = self._create_test_app(timeline_usecase, auth_middleware)
        client = TestClient(app)
        
        # Make request
        entry_id = str(uuid4())
        response = client.get(
            f"/api/v1/timeline/entries/{entry_id}/related?limit=5",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["entry_id"] == entry_id
        assert len(data["related_entries"]) == 1
        assert data["total_count"] == 1

    def test_get_related_entries_query_error(self, mock_container, test_user):
        """Test related entries with query error."""
        container, timeline_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        timeline_usecase.get_related_entries.side_effect = TimelineQueryError("Invalid limit")
        
        # Create app with mocked dependencies
        app = self._create_test_app(timeline_usecase, auth_middleware)
        client = TestClient(app)
        
        # Make request
        entry_id = str(uuid4())
        response = client.get(
            f"/api/v1/timeline/entries/{entry_id}/related",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "Invalid limit" in data["detail"]

    def test_get_related_entries_error(self, mock_container, test_user):
        """Test related entries with general error."""
        container, timeline_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        timeline_usecase.get_related_entries.side_effect = TimelineError("Related entries search failed")
        
        # Create app with mocked dependencies
        app = self._create_test_app(timeline_usecase, auth_middleware)
        client = TestClient(app)
        
        # Make request
        entry_id = str(uuid4())
        response = client.get(
            f"/api/v1/timeline/entries/{entry_id}/related",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "Related entries retrieval failed" in data["detail"]

    def test_timeline_pagination(self, mock_container, test_user):
        """Test timeline pagination parameters."""
        container, timeline_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        
        # Create timeline response with pagination
        timeline_response = TimelineResponse(
            entries=[],
            groups=[],
            total_count=100,
            page=2,
            page_size=10,
            has_next=True,
            has_previous=True,
        )
        timeline_usecase.execute.return_value = timeline_response
        
        # Create app with mocked dependencies
        app = self._create_test_app(timeline_usecase, auth_middleware)
        client = TestClient(app)
        
        # Make request with pagination
        response = client.get(
            "/api/v1/timeline?page=2&page_size=10",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 2
        assert data["page_size"] == 10
        assert data["total_count"] == 100
        assert data["has_next"] is True
        assert data["has_previous"] is True

    def test_timeline_sort_order_validation(self, mock_container, test_user):
        """Test timeline sort order validation."""
        container, timeline_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        
        # Create app with mocked dependencies
        app = self._create_test_app(timeline_usecase, auth_middleware)
        client = TestClient(app)
        
        # Make request with invalid sort order
        response = client.get(
            "/api/v1/timeline?sort_order=invalid",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 422  # Validation error