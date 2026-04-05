"""Integration tests for search API endpoints."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.domain.entities.enums import EntityType
from src.domain.entities.search_result import SearchResponse, SearchResult, SearchScore
from src.domain.entities.thought import Thought, ThoughtMetadata
from src.domain.entities.user import User
from src.domain.exceptions import SearchError, SearchQueryError


@pytest.fixture
def mock_container():
    """Create a mock container with search dependencies."""
    container = Mock()
    
    # Mock search use case
    search_usecase = AsyncMock()
    container.search_thoughts_usecase.return_value = search_usecase
    
    # Mock auth middleware
    auth_middleware = AsyncMock()
    container.auth_middleware.return_value = auth_middleware
    
    return container, search_usecase, auth_middleware


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
def sample_thought():
    """Create a sample thought for testing."""
    return Thought(
        id=uuid4(),
        user_id=uuid4(),
        content="I went to the park today and felt happy",
        timestamp=datetime.now(),
        metadata=ThoughtMetadata(),
        semantic_entries=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_search_response(sample_thought):
    """Create a sample search response."""
    search_result = SearchResult(
        thought=sample_thought,
        matching_entities=[],
        matches=[],
        score=SearchScore(
            semantic_similarity=0.8,
            keyword_match=0.6,
            recency_score=0.9,
            confidence_score=0.7,
            final_score=0.75,
        ),
        rank=1,
    )
    
    return SearchResponse(
        results=[search_result],
        total_count=1,
        page=1,
        page_size=10,
        query_text="park happy",
        search_time_ms=150,
        suggestions=["park", "happy", "today"],
    )


class TestSearchEndpoints:
    """Test cases for search API endpoints."""

    def test_search_thoughts_success(self, mock_container, test_user, sample_search_response):
        """Test successful thought search."""
        container, search_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        search_usecase.execute_with_query.return_value = sample_search_response
        
        # Create app with mocked container
        app = create_app()
        app.container = container
        
        client = TestClient(app)
        
        # Make request
        response = client.post(
            "/api/v1/search",
            json={
                "query_text": "park happy",
                "pagination": {"page": 1, "page_size": 10},
                "highlight_matches": True,
            },
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["query_text"] == "park happy"
        assert data["total_count"] == 1
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["results"]) == 1
        assert data["results"][0]["rank"] == 1
        assert data["results"][0]["score"]["final_score"] == 0.75
        assert len(data["suggestions"]) == 3

    def test_search_thoughts_with_filters(self, mock_container, test_user, sample_search_response):
        """Test thought search with entity and date filters."""
        container, search_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        search_usecase.execute_with_query.return_value = sample_search_response
        
        # Create app with mocked container
        app = create_app()
        app.container = container
        
        client = TestClient(app)
        
        # Make request with filters
        response = client.post(
            "/api/v1/search",
            json={
                "query_text": "park",
                "date_range": {
                    "start_date": "2024-01-01T00:00:00",
                    "end_date": "2024-12-31T23:59:59",
                },
                "entity_filter": {
                    "entity_types": ["location", "emotion"],
                },
                "sort_options": {
                    "sort_by": "date",
                    "sort_order": "desc",
                },
                "pagination": {"page": 1, "page_size": 20},
            },
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["query_text"] == "park"
        
        # Verify the use case was called with correct parameters
        search_usecase.execute_with_query.assert_called_once()
        call_args = search_usecase.execute_with_query.call_args[0][0]
        assert call_args.query_text == "park"
        assert call_args.date_range is not None
        assert call_args.entity_filter is not None
        assert EntityType.LOCATION in call_args.entity_filter.entity_types
        assert EntityType.EMOTION in call_args.entity_filter.entity_types

    def test_search_thoughts_empty_query(self, mock_container, test_user):
        """Test search with empty query text."""
        container, search_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        
        # Create app with mocked container
        app = create_app()
        app.container = container
        
        client = TestClient(app)
        
        # Make request with empty query
        response = client.post(
            "/api/v1/search",
            json={"query_text": ""},
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 422
        data = response.json()
        assert "empty" in data["detail"].lower()

    def test_search_thoughts_query_parsing_error(self, mock_container, test_user):
        """Test search with query parsing error."""
        container, search_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        search_usecase.execute_with_query.side_effect = SearchQueryError("Invalid query syntax")
        
        # Create app with mocked container
        app = create_app()
        app.container = container
        
        client = TestClient(app)
        
        # Make request
        response = client.post(
            "/api/v1/search",
            json={"query_text": "invalid:query:syntax"},
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 422
        data = response.json()
        assert "parsing failed" in data["detail"]

    def test_search_thoughts_search_error(self, mock_container, test_user):
        """Test search with general search error."""
        container, search_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        search_usecase.execute_with_query.side_effect = SearchError("Search service unavailable")
        
        # Create app with mocked container
        app = create_app()
        app.container = container
        
        client = TestClient(app)
        
        # Make request
        response = client.post(
            "/api/v1/search",
            json={"query_text": "test query"},
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "Search failed" in data["detail"]

    def test_search_thoughts_unauthorized(self, mock_container):
        """Test search without authentication."""
        container, search_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.side_effect = Exception("Unauthorized")
        
        # Create app with mocked container
        app = create_app()
        app.container = container
        
        client = TestClient(app)
        
        # Make request without auth header
        response = client.post(
            "/api/v1/search",
            json={"query_text": "test query"},
        )
        
        # Assertions
        assert response.status_code == 500  # Exception handling

    def test_get_search_suggestions_success(self, mock_container, test_user):
        """Test successful search suggestions retrieval."""
        container, search_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        search_usecase.get_suggestions.return_value = ["park", "parking", "parkway"]
        
        # Create app with mocked container
        app = create_app()
        app.container = container
        
        client = TestClient(app)
        
        # Make request
        response = client.get(
            "/api/v1/search/suggestions?query_text=par&limit=3",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["query_text"] == "par"
        assert data["limit"] == 3
        assert len(data["suggestions"]) == 3
        assert "park" in data["suggestions"]
        assert "parking" in data["suggestions"]
        assert "parkway" in data["suggestions"]

    def test_get_search_suggestions_empty_query(self, mock_container, test_user):
        """Test search suggestions with empty query."""
        container, search_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        
        # Create app with mocked container
        app = create_app()
        app.container = container
        
        client = TestClient(app)
        
        # Make request with empty query
        response = client.get(
            "/api/v1/search/suggestions?query_text=",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 422  # Validation error

    def test_get_search_suggestions_limit_validation(self, mock_container, test_user):
        """Test search suggestions with invalid limit."""
        container, search_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        
        # Create app with mocked container
        app = create_app()
        app.container = container
        
        client = TestClient(app)
        
        # Make request with invalid limit
        response = client.get(
            "/api/v1/search/suggestions?query_text=test&limit=25",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 422  # Validation error

    def test_get_entities_success(self, mock_container, test_user, sample_search_response):
        """Test successful entity listing."""
        container, search_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        search_usecase.execute_with_query.return_value = sample_search_response
        
        # Create app with mocked container
        app = create_app()
        app.container = container
        
        client = TestClient(app)
        
        # Make request
        response = client.get(
            "/api/v1/search/entities?entity_types=location&entity_types=emotion&limit=50",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert "entities" in data
        assert "total_count" in data
        assert "entity_types_filter" in data
        assert data["limit"] == 50
        assert data["skip"] == 0

    def test_get_entities_no_filter(self, mock_container, test_user):
        """Test entity listing without filters."""
        container, search_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        
        # Create app with mocked container
        app = create_app()
        app.container = container
        
        client = TestClient(app)
        
        # Make request without filters
        response = client.get(
            "/api/v1/search/entities",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["entities"] == []
        assert data["total_count"] == 0
        assert data["entity_types_filter"] is None

    def test_get_entities_pagination(self, mock_container, test_user, sample_search_response):
        """Test entity listing with pagination."""
        container, search_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        search_usecase.execute_with_query.return_value = sample_search_response
        
        # Create app with mocked container
        app = create_app()
        app.container = container
        
        client = TestClient(app)
        
        # Make request with pagination
        response = client.get(
            "/api/v1/search/entities?entity_types=person&skip=10&limit=20",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["skip"] == 10
        assert data["limit"] == 20

    def test_get_entities_invalid_limit(self, mock_container, test_user):
        """Test entity listing with invalid limit."""
        container, search_usecase, auth_middleware = mock_container
        
        # Setup mocks
        auth_middleware.require_authentication.return_value = test_user
        
        # Create app with mocked container
        app = create_app()
        app.container = container
        
        client = TestClient(app)
        
        # Make request with invalid limit
        response = client.get(
            "/api/v1/search/entities?limit=2000",
            headers={"Authorization": "Bearer test_token"},
        )
        
        # Assertions
        assert response.status_code == 422  # Validation error